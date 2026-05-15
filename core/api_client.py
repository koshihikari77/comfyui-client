import websocket
import uuid
import json
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional
import logging
import sys
import os
from .interfaces import IAPIClient

logger = logging.getLogger(__name__)

class ComfyUI_APIClient(IAPIClient):
    def __init__(self, server_address: str, client_id: Optional[str] = None):
        self.server_address = self._normalize_server_address(server_address)
        self.client_id = client_id or str(uuid.uuid4())
    
    def _normalize_server_address(self, address: str) -> str:
        """
        サーバーアドレスを正規化
        
        Args:
            address: サーバーアドレス（http://host:port または host:port 形式）
            
        Returns:
            正規化済みURL（http://host:port または https://host:port）
        """
        address = address.strip()
        
        # 既にhttp://またはhttps://で始まる場合はそのまま使用
        if address.startswith('http://') or address.startswith('https://'):
            return address
        
        # host:port形式の場合はhttp://を付加
        if ':' in address:
            return f"http://{address}"
        
        # その他の場合はエラー（validate_server_addressで検証済みのはず）
        raise ValueError(f"Invalid server_address format: {address}")

    def queue_prompt(self, workflow: dict) -> str:
        p = {"prompt": workflow, "client_id": self.client_id}
        data = json.dumps(p).encode('utf-8')
        req = urllib.request.Request(
            f"{self.server_address}/prompt",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        try:
            response = json.loads(urllib.request.urlopen(req).read())
            return response['prompt_id']
        except urllib.error.HTTPError as e:
            # ComfyUIは400時にJSONのエラー詳細を返すことがあるので、本文をログに出す
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")
            except Exception:
                body = "<failed to read error body>"
            logger.error("ComfyUI /prompt failed: HTTP %s %s", e.code, e.reason)
            if body:
                logger.error("ComfyUI error body: %s", body)
            raise

    def get_history(self, prompt_id: str) -> dict:
        with urllib.request.urlopen(f"{self.server_address}/history/{prompt_id}") as response:
            return json.loads(response.read())

    def get_image_data(self, filename: str, subfolder: str, folder_type: str) -> bytes:
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url_values = urllib.parse.urlencode(data)
        with urllib.request.urlopen(f"{self.server_address}/view?{url_values}") as response:
            return response.read()

    def get_generated_image(self, prompt_id: str) -> Optional[tuple[str, bytes]]:
        history = self.get_history(prompt_id)
        if not history or prompt_id not in history:
            return None

        prompt_output = history[prompt_id]['outputs']
        for node_id in prompt_output:
            node_output = prompt_output[node_id]
            if 'images' in node_output:
                image = node_output['images'][0]
                image_data = self.get_image_data(image['filename'], image['subfolder'], image['type'])
                return image['filename'], image_data
        return None

    def get_node_text_output(self, prompt_id: str, node_id: str) -> Optional[str]:
        """history.outputs[node_id].text[0] を取得する。
        ShowText|pysssss / WD14Tagger|pysssss などの text/tags 出力ノード用。
        ノードや出力が存在しない場合は None を返す（呼び出し側で握りつぶしてよい）。
        """
        history = self.get_history(prompt_id)
        if not history or prompt_id not in history:
            return None
        outputs = history[prompt_id].get('outputs', {})
        node_out = outputs.get(str(node_id), {})
        # ShowText|pysssss は "text" キー、WD14Tagger|pysssss は "tags" キーで返ることがある
        for key in ("text", "tags"):
            value = node_out.get(key)
            if isinstance(value, list) and value:
                return value[0]
            if isinstance(value, str):
                return value
        return None

    def wait_for_completion(self, prompt_id: str):
        # HTTP URLからWebSocket URLに変換（http:// -> ws://, https:// -> wss://）
        if self.server_address.startswith('https://'):
            ws_base = self.server_address.replace('https://', 'wss://', 1)
        else:
            ws_base = self.server_address.replace('http://', 'ws://', 1)
        ws_url = f"{ws_base}/ws?clientId={self.client_id}"
        
        # websocket.create_connection を使用する
        ws = websocket.create_connection(ws_url, timeout=300) # タイムアウトを追加すると安全
        logger.debug("WebSocket connection established. Waiting for messages...")
        
        try:
            while True:
                # ws.recv()はブロッキング処理なので、データが来るまで待機する
                out = ws.recv()
                if not isinstance(out, str):
                    continue
                logger.debug("RAW MSG: %s", out)

                message = json.loads(out)
                message_type = message.get('type')
                if message_type not in ['executing', 'progress']:
                    logger.debug("Received unhandled message type: %s", message_type)
                    continue
                else:
                    logger.debug("Received message: %s", message)
                
                # 実行完了メッセージをチェック
                if message_type == 'executing':
                    data = message.get('data', {})
                    # 自分のprompt_idに対する、キューの最後の処理完了メッセージ
                    if data.get('node') is None and data.get('prompt_id') == prompt_id:
                        logger.debug("Execution Complete message received.")
                        break  # ループを抜ける
                
                # 進行状況の表示（任意）
                elif message_type == 'progress':
                    if os.getenv("COMFYV_QUIET"):
                        continue
                    data = message.get('data', {})
                    print(
                        f"\r  Progress: {data.get('value', 0)} / {data.get('max', 0)} steps",
                        end="",
                        flush=True,
                        file=sys.stderr,
                    )

        except websocket.WebSocketTimeoutException:
            logger.error("\n❌ WebSocket connection timed out.")
            raise  # エラーを再送出
        except Exception as e:
            logger.error("\n❌ An error occurred in WebSocket communication", exc_info=True)
            raise # エラーを再送出
        finally:
            # 完了時にプログレス表示をクリアするための改行
            if not os.getenv("COMFYV_QUIET"):
                print("\r" + " " * 60 + "\r", end="", file=sys.stderr)
            ws.close()
            logger.debug("WebSocket connection closed.")
