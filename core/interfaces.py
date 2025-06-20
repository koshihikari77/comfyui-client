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