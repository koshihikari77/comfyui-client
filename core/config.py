import yaml
from pathlib import Path

class Config:
    def __init__(self, config_path: str):
        self.path = Path(config_path)
        if not self.path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(self.path, 'r', encoding='utf-8') as f:
            self.data = yaml.safe_load(f)
        
        self._validate()

    def _validate(self):
        required_keys = ['job_name', 'server_address', 'base_workflow', 'variable']
        for key in required_keys:
            if key not in self.data:
                raise ValueError(f"Missing required key in config: '{key}'")
        
        variable = self.data['variable']
        required_var_keys = ['node_id', 'input_name', 'values']
        for key in required_var_keys:
            if key not in variable:
                raise ValueError(f"Missing required key in 'variable': '{key}'")
        
        if not isinstance(variable['values'], list):
            raise TypeError("'variable.values' must be a list.")

    @property
    def job_name(self) -> str:
        return self.data['job_name']

    @property
    def server_address(self) -> str:
        return self.data['server_address']

    @property
    def base_workflow_path(self) -> Path:
        # 設定ファイルからの相対パスとして解釈
        return self.path.parent / self.data['base_workflow']

    @property
    def variable(self) -> dict:
        return self.data['variable']