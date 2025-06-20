from .interfaces import IServiceContainer, IDatabaseManager, IAPIClient, IPromptResolver
from .database import DatabaseManager
from .api_client import ComfyUI_APIClient
from .prompt_resolver import PromptResolver
from .config import Config
import logging

logger = logging.getLogger(__name__)

class ServiceContainer(IServiceContainer):
    """依存関係を管理するサービスコンテナ"""
    
    def __init__(self, config: Config):
        self.config = config
        self._database_manager = None
        self._api_client = None
        self._prompt_resolver = None
        
    def get_database_manager(self) -> IDatabaseManager:
        """DatabaseManagerのシングルトンインスタンスを取得"""
        if self._database_manager is None:
            logger.debug("Creating DatabaseManager instance")
            self._database_manager = DatabaseManager()
        return self._database_manager
    
    def get_api_client(self) -> IAPIClient:
        """APIClientのシングルトンインスタンスを取得"""
        if self._api_client is None:
            logger.debug("Creating ComfyUI_APIClient instance")
            self._api_client = ComfyUI_APIClient(self.config.server_address)
        return self._api_client
    
    def get_prompt_resolver(self) -> IPromptResolver:
        """PromptResolverのシングルトンインスタンスを取得"""
        if self._prompt_resolver is None:
            logger.debug("Creating PromptResolver instance")
            self._prompt_resolver = PromptResolver()
        return self._prompt_resolver 