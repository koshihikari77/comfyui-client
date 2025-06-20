import yaml
from pathlib import Path

class Config:
    _DEFAULT_CONNECTION_CONFIG_PATH = "configs/connection_config.yml"

    def __init__(self, job_config_path: str, connection_config_path: str = None):
        # 1. ジョブ設定の読み込み
        self.job_config_path = Path(job_config_path)
        if not self.job_config_path.exists():
            raise FileNotFoundError(f"Job config file not found: {self.job_config_path}")
        with open(self.job_config_path, 'r', encoding='utf-8') as f:
            self.job_data = yaml.safe_load(f)
        
        # 2. 接続設定の読み込み
        conn_path_str = connection_config_path or self._DEFAULT_CONNECTION_CONFIG_PATH
        self.connection_config_path = Path(conn_path_str)
        if not self.connection_config_path.exists():
            raise FileNotFoundError(f"Connection config file not found: {self.connection_config_path}")
        with open(self.connection_config_path, 'r', encoding='utf-8') as f:
            self.connection_data = yaml.safe_load(f)

        self._validate()

    def _validate(self):
        required_keys = ['job_name', 'base_workflow', 'variables']
        for key in required_keys:
            if key not in self.job_data:
                raise ValueError(f"Missing required key in config: '{key}'")
        # 'variables' がリストであることを確認
        if not isinstance(self.job_data['variables'], list):
            raise TypeError("'variables' must be a list.")

        variable = self.job_data['variables']
        required_var_keys = ['node_id', 'input_name', 'values']
        for v in variable:
            for key in required_var_keys:
                if key not in v:
                    raise ValueError(f"Missing required key in 'variable': '{key}'")
        
            if not isinstance(v['values'], list):
                raise TypeError("'variable.values' must be a list.")
        
        # 接続設定のバリデーション
        if 'server_address' not in self.connection_data:
            raise ValueError("Missing required key in connection config: 'server_address'")

    @property
    def job_name(self) -> str:
        return self.job_data['job_name']

    @property
    def server_address(self) -> str:
        return self.connection_data['server_address']

    @property
    def base_workflow_path(self) -> Path:
        return self.job_config_path.parent / self.job_data['base_workflow']

    @property
    def variables(self) -> dict:
        return self.job_data['variables']
    
    @property
    def job_config_data(self) -> dict:
        return self.job_data

    @property
    def placeholders(self) -> dict:
        return self.job_data.get('placeholders')