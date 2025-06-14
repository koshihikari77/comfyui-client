import websocket
import uuid
import json
import urllib.request
import urllib.parse
from typing import Optional

class ComfyUI_APIClient:
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
        ws = websocket.WebSocket()
        ws.connect(ws_url)
        try:
            while True:
                out = ws.recv()
                if isinstance(out, str):
                    message = json.loads(out)
                    if message['type'] == 'executing':
                        data = message['data']
                        if data.get('node') is None and data.get('prompt_id') == prompt_id:
                            break  # Execution is done
        finally:
            ws.close()