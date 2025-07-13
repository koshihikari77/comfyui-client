import yaml
import logging
from pathlib import Path
from pydantic import ValidationError

from .schemas.config_models import JobConfigModel, ConnectionConfigModel

logger = logging.getLogger(__name__)

class Config:
    def __init__(self, job_config_path: str, connection_config_path: str):
        self.job_config_path = Path(job_config_path)
        self.connection_config_path = Path(connection_config_path)
        
        # ファイルの存在確認
        if not self.job_config_path.exists():
            raise FileNotFoundError(f"Job config file not found: {job_config_path}")
        if not self.connection_config_path.exists():
            raise FileNotFoundError(f"Connection config file not found: {connection_config_path}")
        
        # 設定ファイルを読み込み
        job_raw_data = self._load_yaml(self.job_config_path)
        connection_raw_data = self._load_yaml(self.connection_config_path)
        
        # Pydanticモデルでバリデーション
        self._validate_with_pydantic(job_raw_data, connection_raw_data)
        
        # 後方互換性のため、元のデータも保持
        self.job_data = job_raw_data
        self.connection_data = connection_raw_data

    def _validate_with_pydantic(self, job_raw_data: dict, connection_raw_data: dict):
        """Pydanticモデルを使用してバリデーション"""
        try:
            # ジョブ設定のバリデーション
            self.job_config_model = JobConfigModel(**job_raw_data)
            logger.debug(f"Job config validation successful: {self.job_config_model.job_name}")
            
            # 接続設定のバリデーション
            self.connection_config_model = ConnectionConfigModel(**connection_raw_data)
            logger.debug(f"Connection config validation successful: {self.connection_config_model.server_address}")
            
        except ValidationError as e:
            # PydanticのValidationErrorを従来のエラー形式に変換（後方互換性のため）
            error_str = str(e)
            
            # 特定のエラーパターンを既存のメッセージ形式に変換
            if 'base_workflow' in error_str and '必須です' in error_str:
                raise ValueError("Missing required key in config: 'base_workflow'")
            elif 'variables' in error_str and 'list' in error_str:
                raise TypeError("'variables' must be a list.")
            elif 'Field required' in error_str and 'variables' in error_str:
                if 'input_name' in error_str:
                    raise ValueError("Missing required key in 'variable': 'input_name'")
                elif 'values' in error_str:
                    raise ValueError("Missing required key in 'variable': 'values'")
            elif 'server_address' in error_str:
                raise ValueError("Missing required key in connection config: 'server_address'")
            
            # デフォルトケース: より詳細なエラーメッセージ
            error_messages = []
            for error in e.errors():
                field_path = '.'.join(str(loc) for loc in error['loc'])
                error_messages.append(f"Field '{field_path}': {error['msg']}")
            
            if 'variables' in error_str or 'job_name' in error_str or 'base_workflow' in error_str:
                raise ValueError(f"Config validation failed: {'; '.join(error_messages)}")
            elif 'server_address' in error_str:
                raise ValueError(f"Connection config validation failed: {'; '.join(error_messages)}")
            else:
                raise TypeError(f"Type validation failed: {'; '.join(error_messages)}")
    
    def _validate(self):
        """既存のメソッド（後方互換性のため保持、内部でPydanticを使用）"""
        # Pydanticバリデーションが既に実行されているので、何もしない
        pass

    def _load_yaml(self, file_path: Path) -> dict:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"YAML parsing error in {file_path}: {e}")
        except Exception as e:
            raise IOError(f"Error reading {file_path}: {e}")

    @property
    def job_name(self) -> str:
        return self.job_data['job_name']

    @property
    def server_address(self) -> str:
        return self.connection_data['server_address']

    @property
    def variables(self) -> list:
        return self.job_data.get('variables', [])

    @property
    def prompts(self) -> list:
        """シーケンスジョブ用のプロンプト定義"""
        return self.job_data.get('prompts', [])

    @property
    def placeholders(self) -> dict:
        return self.job_data.get('placeholders', {})

    @property
    def job_config_data(self) -> dict:
        return self.job_data

    @property
    def fixed_parameters(self) -> list:
        return self.job_data.get('fixed_parameters', [])

    @property
    def random_parameters(self) -> list:
        return self.job_data.get('random_parameters', [])

    @property
    def base_workflow_path(self) -> Path:
        if 'base_workflow' not in self.job_data:
            return None
        
        workflow_filename = self.job_data['base_workflow']
        
        # 絶対パスまたは相対パスで直接指定されている場合
        if Path(workflow_filename).is_absolute():
            return Path(workflow_filename)
        
        # 相対パスの場合の解決
        # 1. 標準的なディレクトリ構造の場合を優先
        # job_config_pathが configs/jobs/xxx.yaml の場合、
        # configs/ ディレクトリを基準にする
        if self.job_config_path.parent.name == 'jobs':
            configs_dir = self.job_config_path.parent.parent
            standard_path = configs_dir / workflow_filename
            return standard_path
            
        # 2. job_config_pathと同じディレクトリにある場合（フラットな構造のテスト用）
        same_dir_path = self.job_config_path.parent / workflow_filename
        return same_dir_path