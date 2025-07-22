from .interfaces import IServiceContainer, IDatabaseManager, IAPIClient, IPromptResolver
from .database import DatabaseManager
from .api_client import ComfyUI_APIClient
from .prompt_resolver import PromptResolver
from .prompt_resolver_v2 import PromptResolverV2
from .config import Config
import logging
import os

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
    
    def get_prompt_resolver(self, use_v2: bool = True) -> IPromptResolver:
        """
        PromptResolverのシングルトンインスタンスを取得
        
        Args:
            use_v2: V2パイプラインを使用するか（None時は環境変数で判定）
            
        Returns:
            IPromptResolver: V1またはV2のPromptResolverインスタンス
        """
        if self._prompt_resolver is None:
            # V2使用判定（優先順位）
            # 1. 明示的パラメータ
            # 2. 環境変数PROMPT_RESOLVER_V2
            # 3. デフォルト（False = V1）
            if use_v2 is None:
                use_v2 = os.getenv('PROMPT_RESOLVER_V2', 'false').lower() in ('true', '1', 'yes', 'on')
            
            if use_v2:
                logger.debug("Creating PromptResolverV2 instance")
                # V2設定構築（configから必要な設定を抽出）
                v2_config = {
                    'ignore_tags': getattr(self.config, 'ignore_tags', []),
                    'ignore_groups': getattr(self.config, 'ignore_groups', []),
                    'placeholders': getattr(self.config, 'placeholders', {}),
                    'locale': getattr(self.config, 'locale', ','),
                    'strict_level': getattr(self.config, 'strict_level', 'warn'),
                    'seed': getattr(self.config, 'seed', None)
                }
                self._prompt_resolver = PromptResolverV2("configs/prompts", v2_config)
                logger.info("🚀 PromptResolverV2 pipeline enabled")
            else:
                logger.debug("Creating PromptResolver (V1) instance")
                self._prompt_resolver = PromptResolver("configs/prompts")
                logger.info("📊 PromptResolver V1 (legacy) mode")
                
        return self._prompt_resolver
    
    def get_prompt_resolver_v1(self) -> PromptResolver:
        """明示的にV1 PromptResolverを取得"""
        return PromptResolver("configs/prompts")
    
    def get_prompt_resolver_v2(self, config: dict = None) -> PromptResolverV2:
        """明示的にV2 PromptResolverを取得"""
        v2_config = config or {
            'ignore_tags': getattr(self.config, 'ignore_tags', []),
            'ignore_groups': getattr(self.config, 'ignore_groups', []),
            'placeholders': getattr(self.config, 'placeholders', {}),
            'locale': getattr(self.config, 'locale', ','),
            'strict_level': getattr(self.config, 'strict_level', 'warn'),
            'seed': getattr(self.config, 'seed', None)
        }
        return PromptResolverV2("configs/prompts", v2_config)