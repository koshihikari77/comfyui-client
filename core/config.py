import yaml
import logging
from pathlib import Path

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
        self.job_data = self._load_yaml(self.job_config_path)
        self.connection_data = self._load_yaml(self.connection_config_path)
        
        # バリデーション
        self._validate()

    def _validate(self):
        # 共通必須キー
        if 'job_name' not in self.job_data:
            raise ValueError("Missing required key in config: 'job_name'")
        
        job_type = self.job_data.get('job_type', 'grid_search')
        
        # ジョブタイプ別のバリデーション
        if job_type == 'grid_search':
            # グリッドサーチでは base_workflow と variables が必須
            if 'base_workflow' not in self.job_data:
                raise ValueError("Missing required key in config: 'base_workflow'")
            if 'variables' not in self.job_data:
                raise ValueError("Missing required key in config: 'variables'")
            
            # 'variables' がリストであることを確認
            if not isinstance(self.job_data['variables'], list):
                raise TypeError("'variables' must be a list.")

            variables = self.job_data['variables']
            required_var_keys = ['node_id', 'input_name', 'values']
            for v in variables:
                for key in required_var_keys:
                    if key not in v:
                        raise ValueError(f"Missing required key in 'variable': '{key}'")
            
                if not isinstance(v['values'], list):
                    raise TypeError("'variable.values' must be a list.")
                    
        elif job_type == 'sequence':
            # シーケンスでは prompts が必須
            if 'prompts' not in self.job_data:
                raise ValueError("Missing required key in config: 'prompts'")
            
            if not isinstance(self.job_data['prompts'], list):
                raise TypeError("'prompts' must be a list.")
                
        # 接続設定のバリデーション
        if 'server_address' not in self.connection_data:
            raise ValueError("Missing required key in connection config: 'server_address'")

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