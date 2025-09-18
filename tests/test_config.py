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
    
    def test_sequence_job_with_new_prompt_format(self, temp_config_dir, sample_connection_config):
        """sequenceジョブの新プロンプト形式（List[str]）のテスト"""
        jobs_dir = temp_config_dir / 'jobs'
        jobs_dir.mkdir()
        
        config_data = {
            'job_name': 'sequence_test',
            'job_type': 'sequence',
            'default_runs': 2,
            'prompts': [
                # 新形式1: List[str]
                ["1girl", "<preset:character>", "school_uniform"],
                # 新形式2: フロースタイル
                ["1boy", "suit", "office"],
                # 従来形式との混在
                {
                    "template": "1girl, casual clothes",
                    "runs": 3
                }
            ]
        }
        
        config_path = jobs_dir / 'sequence_test.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False)
        
        config = Config(
            job_config_path=str(config_path),
            connection_config_path=str(sample_connection_config)
        )
        
        # プロンプトが正規化されているかテスト
        assert len(config.prompts) == 3
        assert config.prompts[0].template == "1girl, <preset:character>, school_uniform"
        assert config.prompts[0].runs is None  # default_runsを使用
        assert config.prompts[1].template == "1boy, suit, office"
        assert config.prompts[1].runs is None
        assert config.prompts[2].template == "1girl, casual clothes"
        assert config.prompts[2].runs == 3
    
    def test_sequence_job_validation_errors(self, temp_config_dir, sample_connection_config):
        """sequenceジョブのバリデーションエラーテスト"""
        jobs_dir = temp_config_dir / 'jobs'
        jobs_dir.mkdir()
        
        # プロンプトが空の場合
        config_data = {
            'job_name': 'sequence_test',
            'job_type': 'sequence',
            'prompts': []
        }
        
        config_path = jobs_dir / 'empty_prompts.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False)
        
        with pytest.raises(ValueError, match="sequenceジョブではpromptsが必須です"):
            Config(
                job_config_path=str(config_path),
                connection_config_path=str(sample_connection_config)
            )
    
    def test_invalid_prompt_format(self, temp_config_dir, sample_connection_config):
        """無効なプロンプト形式のエラーテスト"""
        jobs_dir = temp_config_dir / 'jobs'
        jobs_dir.mkdir()
        
        config_data = {
            'job_name': 'sequence_test',
            'job_type': 'sequence',
            'prompts': [
                "invalid_string_format"  # PromptModel、List[str]、Dict以外
            ]
        }
        
        config_path = jobs_dir / 'invalid_prompt.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False)
        
        with pytest.raises(ValueError, match="無効なプロンプト形式"):
            Config(
                job_config_path=str(config_path),
                connection_config_path=str(sample_connection_config)
            )
    
    def test_iterator_configuration(self, temp_config_dir, sample_connection_config):
        """Iterator設定のテスト"""
        jobs_dir = temp_config_dir / 'jobs'
        jobs_dir.mkdir()
        
        config_data = {
            'job_name': 'iterator_test',
            'job_type': 'sequence',
            'prompts': [
                {
                    "template": "1girl, $[location], $[style]",
                    "runs": 3
                }
            ],
            'iterators': {
                'location': ['library', 'cafe', 'spaceport'],
                'style': {
                    'expand_preset': 'expression'
                }
            }
        }
        
        config_path = jobs_dir / 'iterator_test.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False)
        
        config = Config(
            job_config_path=str(config_path),
            connection_config_path=str(sample_connection_config)
        )
        
        assert hasattr(config, 'iterators')
        assert config.iterators is not None
        assert 'location' in config.iterators
        assert 'style' in config.iterators
        assert config.iterators['location'] == ['library', 'cafe', 'spaceport']
        assert config.iterators['style']['expand_preset'] == 'expression'
    
    def test_iterator_validation_errors(self, temp_config_dir, sample_connection_config):
        """Iterator設定のバリデーションエラーテスト"""
        jobs_dir = temp_config_dir / 'jobs'
        jobs_dir.mkdir()
        
        # 空のIteratorリスト
        config_data = {
            'job_name': 'iterator_test',
            'job_type': 'sequence',
            'prompts': [{"template": "test", "runs": 1}],
            'iterators': {
                'empty_list': []
            }
        }
        
        config_path = jobs_dir / 'empty_iterator.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False)
        
        with pytest.raises(ValueError, match="は空でないリストである必要があります"):
            Config(
                job_config_path=str(config_path),
                connection_config_path=str(sample_connection_config)
            )
        
        # expand_presetキーなしの辞書
        config_data['iterators'] = {
            'invalid_dict': {'missing_key': 'value'}
        }
        
        config_path = jobs_dir / 'invalid_dict.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False)
        
        with pytest.raises(ValueError, match="'expand_preset' キーが必要です"):
            Config(
                job_config_path=str(config_path),
                connection_config_path=str(sample_connection_config)
            )