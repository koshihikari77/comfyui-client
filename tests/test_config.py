"""
Configクラスのテスト
"""
import pytest
import yaml
from pathlib import Path

from core.config import Config


class TestConfig:
    """Configクラスのテストケース"""
    
    def test_valid_config_initialization(self, sample_job_config, sample_connection_config):
        """正常な設定でのConfig初期化テスト"""
        config = Config(
            job_config_path=str(sample_job_config),
            connection_config_path=str(sample_connection_config)
        )
        
        assert config.job_name == 'test_job'
        assert config.server_address == 'http://localhost:8188'
        assert len(config.variables) == 1
        assert config.variables[0]['node_id'] == 1
        assert config.variables[0]['input_name'] == 'test_param'
        assert config.variables[0]['values'] == ['value1', 'value2']
    
    def test_missing_job_config_file(self, sample_connection_config):
        """存在しないジョブ設定ファイルでのエラーテスト"""
        with pytest.raises(FileNotFoundError, match="Job config file not found"):
            Config(
                job_config_path="nonexistent_job.yaml",
                connection_config_path=str(sample_connection_config)
            )
    
    def test_missing_connection_config_file(self, sample_job_config):
        """存在しない接続設定ファイルでのエラーテスト"""
        with pytest.raises(FileNotFoundError, match="Connection config file not found"):
            Config(
                job_config_path=str(sample_job_config),
                connection_config_path="nonexistent_connection.yaml"
            )
    
    def test_missing_required_job_keys(self, temp_config_dir, sample_connection_config):
        """必須キーが不足しているジョブ設定でのエラーテスト"""
        # jobs サブディレクトリを作成
        jobs_dir = temp_config_dir / 'jobs'
        jobs_dir.mkdir()
        
        invalid_config_data = {
            'job_name': 'test_job'
            # 'base_workflow' と 'variables' が不足
        }
        
        config_path = jobs_dir / 'invalid_job.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(invalid_config_data, f, default_flow_style=False)
        
        with pytest.raises(ValueError, match="Missing required key in config"):
            Config(
                job_config_path=str(config_path),
                connection_config_path=str(sample_connection_config)
            )
    
    def test_invalid_variables_format(self, temp_config_dir, sample_connection_config):
        """variablesの形式が正しくない場合のエラーテスト"""
        # jobs サブディレクトリを作成
        jobs_dir = temp_config_dir / 'jobs'
        jobs_dir.mkdir()
        
        invalid_config_data = {
            'job_name': 'test_job',
            'base_workflow': 'test.json',
            'variables': 'not_a_list'  # リストではない
        }
        
        config_path = jobs_dir / 'invalid_variables.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(invalid_config_data, f, default_flow_style=False)
        
        with pytest.raises(TypeError, match="'variables' must be a list"):
            Config(
                job_config_path=str(config_path),
                connection_config_path=str(sample_connection_config)
            )
    
    def test_missing_variable_keys(self, temp_config_dir, sample_connection_config):
        """variable内の必須キーが不足している場合のエラーテスト"""
        # jobs サブディレクトリを作成
        jobs_dir = temp_config_dir / 'jobs'
        jobs_dir.mkdir()
        
        invalid_config_data = {
            'job_name': 'test_job',
            'base_workflow': 'test.json',
            'variables': [
                {
                    'node_id': 1,
                    # 'input_name' と 'values' が不足
                }
            ]
        }
        
        config_path = jobs_dir / 'invalid_variable_keys.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(invalid_config_data, f, default_flow_style=False)
        
        with pytest.raises(ValueError, match="Missing required key in 'variable'"):
            Config(
                job_config_path=str(config_path),
                connection_config_path=str(sample_connection_config)
            )
    
    def test_placeholders_property(self, temp_config_dir, sample_connection_config):
        """placeholdersプロパティのテスト"""
        # jobs サブディレクトリを作成
        jobs_dir = temp_config_dir / 'jobs'
        jobs_dir.mkdir()
        
        # workflows サブディレクトリを作成
        workflows_dir = temp_config_dir / 'workflows'
        workflows_dir.mkdir()
        
        config_data = {
            'job_name': 'test_job',
            'base_workflow': 'workflows/test.json',
            'variables': [
                {
                    'node_id': 1,
                    'input_name': 'test_param',
                    'values': ['value1', 'value2']
                }
            ],
            'placeholders': {
                'character': ['Alice', 'Bob'],
                'location': ['Tokyo', 'Paris']
            }
        }
        
        config_path = jobs_dir / 'with_placeholders.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False)
        
        # ワークフローファイルも作成
        import json
        workflow_data = {"1": {"inputs": {"test_param": "default"}, "class_type": "TestNode"}}
        workflow_path = workflows_dir / 'test.json'
        with open(workflow_path, 'w', encoding='utf-8') as f:
            json.dump(workflow_data, f)
        
        config = Config(
            job_config_path=str(config_path),
            connection_config_path=str(sample_connection_config)
        )
        
        assert config.placeholders is not None
        assert 'character' in config.placeholders
        assert config.placeholders['character'] == ['Alice', 'Bob']
    
    def test_base_workflow_path_property(self, sample_job_config, sample_connection_config):
        """base_workflow_pathプロパティのテスト"""
        config = Config(
            job_config_path=str(sample_job_config),
            connection_config_path=str(sample_connection_config)
        )

        # sample_job_configのbase_workflowは 'workflows/test_workflow.json' 
        # sample_job_configは /tmp/xxx/jobs/test_job.yaml なので、
        # /tmp/xxx/workflows/test_workflow.json になるはず  
        expected_path = sample_job_config.parent.parent / 'workflows' / 'test_workflow.json'
        assert config.base_workflow_path == expected_path 