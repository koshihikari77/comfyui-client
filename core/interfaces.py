from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Any
import sqlite3

class IDatabaseManager(ABC):
    """データベース管理の抽象インターフェース"""
    
    @abstractmethod
    def create_job(self, job_name: str, config_data: dict) -> int:
        pass
    
    @abstractmethod
    def complete_job(self, job_id: int):
        pass
    
    @abstractmethod
    def create_image_record(self, job_id: int, workflow: dict) -> int:
        pass
    
    @abstractmethod
    def update_image_record(self, image_id: int, filepath: str, status: str):
        pass

    @abstractmethod
    def update_image_tags(self, image_id: int, tags: List[str], model: str = None):
        pass

    @abstractmethod
    def get_images_by_job_id(self, job_id: int) -> List[sqlite3.Row]:
        pass
    
    @abstractmethod
    def close(self):
        pass


class IAPIClient(ABC):
    """ComfyUI API クライアントの抽象インターフェース"""
    
    @abstractmethod
    def queue_prompt(self, workflow: dict) -> str:
        pass
    
    @abstractmethod
    def wait_for_completion(self, prompt_id: str):
        pass
    
    @abstractmethod
    def get_generated_image(self, prompt_id: str) -> Optional[tuple[str, bytes]]:
        pass


class IPromptResolver(ABC):
    """プロンプト解決の抽象インターフェース"""
    
    @abstractmethod
    def resolve(self, template_string: str) -> str:
        pass
    
    @abstractmethod
    def resolve_full(self, template: str, placeholders: dict | None = None) -> str:
        """Preset → Placeholder → Wildcard の順で 1 つの文字列を解決"""
        pass
    
    @abstractmethod
    def expand_placeholders(self, template: str, placeholders: dict) -> list[str]:
        """プレースホルダーの全組合せを生成"""
        pass

    def resolve_nth(
        self, template_string: str, n: int, cycle: bool = True, placeholders: dict | None = None
    ) -> str:
        """n 番目の直積組み合わせで解決（Sequence/dump 用）。未実装時は resolve にフォールバック。"""
        return self.resolve_full(template_string, placeholders)


class IServiceContainer(ABC):
    """サービスコンテナの抽象インターフェース"""
    
    @abstractmethod
    def get_database_manager(self) -> IDatabaseManager:
        pass
    
    @abstractmethod
    def get_api_client(self) -> IAPIClient:
        pass
    
    @abstractmethod
    def get_prompt_resolver(self) -> IPromptResolver:
        pass 