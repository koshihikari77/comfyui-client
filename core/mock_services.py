"""
テスト用のモック実装
依存性注入により、本来のサービスをモックに置き換えることが可能になります
"""
from typing import Optional, List
import sqlite3
import json
import logging
from .interfaces import IDatabaseManager, IAPIClient, IPromptResolver, IServiceContainer

logger = logging.getLogger(__name__)

class MockDatabaseManager(IDatabaseManager):
    """テスト用のモックデータベースマネージャー"""
    
    def __init__(self):
        self.jobs = {}
        self.images = {}
        self.next_job_id = 1
        self.next_image_id = 1
        logger.debug("MockDatabaseManager initialized")
    
    def create_job(self, job_name: str, config_data: dict) -> int:
        job_id = self.next_job_id
        self.jobs[job_id] = {
            'id': job_id,
            'name': job_name,
            'config': json.dumps(config_data),
            'status': 'running'
        }
        self.next_job_id += 1
        logger.debug(f"Mock: Created job {job_id}")
        return job_id
    
    def complete_job(self, job_id: int):
        if job_id in self.jobs:
            self.jobs[job_id]['status'] = 'completed'
        logger.debug(f"Mock: Completed job {job_id}")
    
    def create_image_record(self, job_id: int, workflow: dict, parameters: dict = None) -> int:
        image_id = self.next_image_id
        self.images[image_id] = {
            'id': image_id,
            'job_id': job_id,
            'workflow': json.dumps(workflow),
            'parameters': json.dumps(parameters) if parameters is not None else None,
            'status': 'pending',
            'filepath': None
        }
        self.next_image_id += 1
        logger.debug(f"Mock: Created image record {image_id}")
        return image_id
    
    def update_image_record(self, image_id: int, filepath: str, status: str):
        if image_id in self.images:
            self.images[image_id]['filepath'] = filepath
            self.images[image_id]['status'] = status
        logger.debug(f"Mock: Updated image {image_id} to {status}")

    def update_image_tags(self, image_id: int, tags: List[str], model: str = None):
        if image_id in self.images:
            self.images[image_id]['tags_json'] = {"model": model, "tags": list(tags)}
        logger.debug(f"Mock: Tagged image {image_id} with {len(tags)} tags")

    def get_images_by_job_id(self, job_id: int) -> List[dict]:
        # Note: 実際のsqlite3.Rowの代わりに辞書を返す
        return [img for img in self.images.values() if img['job_id'] == job_id and img['status'] == 'success']
    
    def close(self):
        logger.debug("Mock: Database closed")


class MockAPIClient(IAPIClient):
    """テスト用のモックAPIクライアント"""
    
    def __init__(self):
        self.prompt_counter = 1
        logger.debug("MockAPIClient initialized")
    
    def queue_prompt(self, workflow: dict) -> str:
        prompt_id = f"mock_prompt_{self.prompt_counter}"
        self.prompt_counter += 1
        logger.debug(f"Mock: Queued prompt {prompt_id}")
        return prompt_id
    
    def wait_for_completion(self, prompt_id: str):
        logger.debug(f"Mock: Waiting for completion of {prompt_id} (immediately completed)")
    
    def get_generated_image(self, prompt_id: str) -> Optional[tuple[str, bytes]]:
        # テスト用のダミー画像データ
        fake_image_data = b"FAKE_PNG_DATA"
        logger.debug(f"Mock: Generated fake image for {prompt_id}")
        return f"mock_image_{prompt_id}.png", fake_image_data


class MockPromptResolver(IPromptResolver):
    """テスト用のモックプロンプトリゾルバー"""
    
    def resolve(self, template_string: str) -> str:
        # 単純にテンプレートをそのまま返す（プレフィックス付き）
        resolved = f"[MOCK_RESOLVED] {template_string}"
        logger.debug(f"Mock: Resolved '{template_string}' to '{resolved}'")
        return resolved
    
    def resolve_full(self, template: str, placeholders: dict | None = None) -> str:
        # テスト用の簡単な実装
        resolved = f"[MOCK_RESOLVED_FULL] {template}"
        if placeholders:
            resolved += f" [PLACEHOLDERS: {placeholders}]"
        logger.debug(f"Mock: Resolved full '{template}' to '{resolved}'")
        return resolved
    
    def expand_placeholders(self, template: str, placeholders: dict) -> list[str]:
        # テスト用の簡単な実装 - プレースホルダーの組み合わせを展開
        import re
        import itertools
        
        placeholder_names = re.findall(r'{(.*?)}', template)
        if not placeholder_names:
            return [template]
        
        # 各プレースホルダーの値リストを取得
        value_lists = [placeholders[name] for name in placeholder_names]
        combinations = list(itertools.product(*value_lists))
        
        # 各組み合わせを元のテンプレートに埋め込んで最終的な文字列リストを作成
        expanded_strings = []
        for combo in combinations:
            temp_string = template
            for name, value in zip(placeholder_names, combo):
                temp_string = temp_string.replace(f'{{{name}}}', str(value), 1)
            expanded_strings.append(temp_string)
        
        logger.debug(f"Mock: Expanded '{template}' into {len(expanded_strings)} prompts")
        return expanded_strings


class MockServiceContainer(IServiceContainer):
    """テスト用のモックサービスコンテナ"""
    
    def __init__(self):
        self._database_manager = MockDatabaseManager()
        self._api_client = MockAPIClient()
        self._prompt_resolver = MockPromptResolver()
        logger.debug("MockServiceContainer initialized")
    
    def get_database_manager(self) -> IDatabaseManager:
        return self._database_manager
    
    def get_api_client(self) -> IAPIClient:
        return self._api_client
    
    def get_prompt_resolver(self) -> IPromptResolver:
        return self._prompt_resolver 