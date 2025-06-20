import websocket
import uuid
import json
import urllib.request
import urllib.parse
from typing import Optional
import logging
from .interfaces import IAPIClient

logger = logging.getLogger(__name__)

class ComfyUI_APIClient(IAPIClient):
    def __init__(self, server_address: str, client_id: Optional[str] = None):
        self.server_address = server_address
        self.client_id = client_id or str(uuid.uuid4())

    def queue_prompt(self, workflow: dict) -> str:
        p = {"prompt": workflow, "client_id": self.client_id}
        data = json.dumps(p).encode('utf-8')
        req = urllib.request.Request(f"http://{self.server_address}/prompt", data=data)
        response = json.loads(urllib.request.urlopen(req).read())
        return response['prompt_id']

    def get_history(self, prompt_id: str) -> dict:
        with urllib.request.urlopen(f"http://{self.server_address}/history/{prompt_id}") as response:
            return json.loads(response.read())

    def get_image_data(self, filename: str, subfolder: str, folder_type: str) -> bytes:
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url_values = urllib.parse.urlencode(data)
        with urllib.request.urlopen(f"http://{self.server_address}/view?{url_values}") as response:
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

    def wait_for_completion(self, prompt_id: str):
        ws_url = f"ws://{self.server_address}/ws?clientId={self.client_id}"
        
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
                    data = message.get('data', {})
                    print(f"\r  Progress: {data.get('value', 0)} / {data.get('max', 0)} steps", end="", flush=True)

        except websocket.WebSocketTimeoutException:
            logger.error("\n❌ WebSocket connection timed out.")
            raise  # エラーを再送出
        except Exception as e:
            logger.error("\n❌ An error occurred in WebSocket communication", exc_info=True)
            raise # エラーを再送出
        finally:
            # 完了時にプログレス表示をクリアするための改行
            print("\r" + " " * 60 + "\r", end="") 
            ws.close()
            logger.debug("WebSocket connection closed.")