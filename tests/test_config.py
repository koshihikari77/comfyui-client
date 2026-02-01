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
        # Pydanticモデルなので属性アクセスを使用
        assert config.variables[0].node_id == 1
        assert config.variables[0].input_name == 'test_param'
        assert config.variables[0].values == ['value1', 'value2']
    
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

    def test_base_workflow_path_property_nested_jobs_dir(self, temp_config_dir, sample_connection_config):
        """base_workflow_path: configs/jobs/** 配下でも configs/ 基準で解決されること"""
        jobs_dir = temp_config_dir / 'jobs' / 'pixiv' / 'pink_salon'
        jobs_dir.mkdir(parents=True)
        workflows_dir = temp_config_dir / 'workflows'
        workflows_dir.mkdir()

        # テスト用ワークフロー作成
        import json
        workflow_data = {"1": {"inputs": {"text": "default"}, "class_type": "TestNode"}}
        workflow_path = workflows_dir / 'test_workflow.json'
        with open(workflow_path, 'w', encoding='utf-8') as f:
            json.dump(workflow_data, f)

        # ネストしたjob config
        config_data = {
            'job_name': 'nested_job',
            'job_type': 'grid_search',
            'base_workflow': 'workflows/test_workflow.json',
            'variables': [
                {'node_id': 1, 'input_name': 'test_param', 'values': ['value1']}
            ]
        }
        config_path = jobs_dir / 'nested_job.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False)

        config = Config(
            job_config_path=str(config_path),
            connection_config_path=str(sample_connection_config)
        )
        assert config.base_workflow_path == workflow_path
    
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

    def test_parameter_combinations_configuration(self, temp_config_dir, sample_connection_config):
        """パラメータ組み合わせ設定の正常読み込みテスト"""
        jobs_dir = temp_config_dir / 'jobs'
        jobs_dir.mkdir(exist_ok=True)
        
        config_data = {
            'job_name': 'parameter_combinations_test',
            'job_type': 'sequence',
            'prompts': [
                {'template': 'test prompt', 'runs': 4}
            ],
            'parameter_combinations': [
                {
                    'name': 'high_quality',
                    'parameters': [
                        {'node_id': 220, 'input_name': 'width', 'value': 1024},
                        {'node_id': 220, 'input_name': 'height', 'value': 1024},
                        {'node_id': 54, 'input_name': 'model_weight_1', 'value': 0.8}
                    ]
                },
                {
                    'name': 'artistic_portrait',
                    'parameters': [
                        {'node_id': 220, 'input_name': 'width', 'value': 768},
                        {'node_id': 220, 'input_name': 'height', 'value': 1344},
                        {'node_id': 54, 'input_name': 'model_weight_1', 'value': 0.6}
                    ]
                }
            ]
        }
        
        config_path = jobs_dir / 'param_combinations.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False)
        
        config = Config(
            job_config_path=str(config_path),
            connection_config_path=str(sample_connection_config)
        )
        
        # パラメータ組み合わせの確認
        combinations = config.parameter_combinations
        assert len(combinations) == 2
        
        # 1つ目の組み合わせ確認
        first_combination = combinations[0]
        assert first_combination.name == 'high_quality'
        assert len(first_combination.parameters) == 3
        
        # パラメータの詳細確認
        width_param = first_combination.parameters[0]
        assert width_param.node_id == 220
        assert width_param.input_name == 'width'
        assert width_param.value == 1024
        
        # 2つ目の組み合わせ確認
        second_combination = combinations[1]
        assert second_combination.name == 'artistic_portrait'
        assert len(second_combination.parameters) == 3

    def test_server_address_http_format(self, temp_config_dir, sample_job_config):
        """server_addressのhttp://形式のテスト"""
        connection_data = {
            'server_address': 'http://localhost:8188'
        }
        
        connection_path = temp_config_dir / 'connection_http.yaml'
        with open(connection_path, 'w', encoding='utf-8') as f:
            yaml.dump(connection_data, f, default_flow_style=False)
        
        config = Config(
            job_config_path=str(sample_job_config),
            connection_config_path=str(connection_path)
        )
        
        assert config.server_address == 'http://localhost:8188'
    
    def test_server_address_host_port_format(self, temp_config_dir, sample_job_config):
        """server_addressのhost:port形式のテスト"""
        connection_data = {
            'server_address': 'localhost:8188'
        }
        
        connection_path = temp_config_dir / 'connection_hostport.yaml'
        with open(connection_path, 'w', encoding='utf-8') as f:
            yaml.dump(connection_data, f, default_flow_style=False)
        
        config = Config(
            job_config_path=str(sample_job_config),
            connection_config_path=str(connection_path)
        )
        
        assert config.server_address == 'localhost:8188'
    
    def test_server_address_https_format(self, temp_config_dir, sample_job_config):
        """server_addressのhttps://形式のテスト"""
        connection_data = {
            'server_address': 'https://example.com:8188'
        }
        
        connection_path = temp_config_dir / 'connection_https.yaml'
        with open(connection_path, 'w', encoding='utf-8') as f:
            yaml.dump(connection_data, f, default_flow_style=False)
        
        config = Config(
            job_config_path=str(sample_job_config),
            connection_config_path=str(connection_path)
        )
        
        assert config.server_address == 'https://example.com:8188'
    
    def test_server_address_invalid_format(self, temp_config_dir, sample_job_config):
        """server_addressの無効な形式のテスト"""
        connection_data = {
            'server_address': 'invalid_format'
        }
        
        connection_path = temp_config_dir / 'connection_invalid.yaml'
        with open(connection_path, 'w', encoding='utf-8') as f:
            yaml.dump(connection_data, f, default_flow_style=False)
        
        with pytest.raises(ValueError, match="server_addressは有効なURL形式"):
            Config(
                job_config_path=str(sample_job_config),
                connection_config_path=str(connection_path)
            )
    
    def test_parameter_combinations_validation_errors(self, temp_config_dir, sample_connection_config):
        """パラメータ組み合わせのバリデーションエラーテスト"""
        jobs_dir = temp_config_dir / 'jobs'
        jobs_dir.mkdir(exist_ok=True)
        
        # 重複する組み合わせ名
        config_data = {
            'job_name': 'duplicate_test',
            'job_type': 'sequence',
            'prompts': [{'template': 'test', 'runs': 1}],
            'parameter_combinations': [
                {
                    'name': 'duplicate_name',
                    'parameters': [
                        {'node_id': 220, 'input_name': 'width', 'value': 1024}
                    ]
                },
                {
                    'name': 'duplicate_name',  # 重複
                    'parameters': [
                        {'node_id': 220, 'input_name': 'height', 'value': 1024}
                    ]
                }
            ]
        }
        
        config_path = jobs_dir / 'duplicate_names.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False)
        
        with pytest.raises(ValueError, match="Parameter combination名 'duplicate_name' が重複しています"):
            Config(
                job_config_path=str(config_path),
                connection_config_path=str(sample_connection_config)
            )
        
        # 組み合わせ内の重複パラメータ
        config_data['parameter_combinations'] = [
            {
                'name': 'duplicate_params',
                'parameters': [
                    {'node_id': 220, 'input_name': 'width', 'value': 1024},
                    {'node_id': 220, 'input_name': 'width', 'value': 512}  # 重複
                ]
            }
        ]
        
        config_path = jobs_dir / 'duplicate_params.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False)
        
        with pytest.raises(ValueError, match="重複するパラメータが検出されました: node_id=220, input_name=width"):
            Config(
                job_config_path=str(config_path),
                connection_config_path=str(sample_connection_config)
            )
        
        # 無効なnode_id
        config_data['parameter_combinations'] = [
            {
                'name': 'invalid_node_id',
                'parameters': [
                    {'node_id': 0, 'input_name': 'width', 'value': 1024}  # 0は無効
                ]
            }
        ]
        
        config_path = jobs_dir / 'invalid_node_id.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False)
        
        with pytest.raises(ValueError, match="node_idは正の整数である必要があります"):
            Config(
                job_config_path=str(config_path),
                connection_config_path=str(sample_connection_config)
            )


class TestPromptsDelta:
    """prompts_delta コンパイラのテストケース"""
    
    def test_basic_prompts_delta(self, temp_config_dir, sample_connection_config):
        """基本的なprompts_delta（差分のみ）のテスト"""
        jobs_dir = temp_config_dir / 'jobs'
        jobs_dir.mkdir(exist_ok=True)
        
        config_data = {
            'job_name': 'prompts_delta_test',
            'job_type': 'sequence',
            'prompt_template': {
                'order': ['quality', 'subject', 'action', 'location'],
                'slots': {
                    'quality': 'masterpiece, best quality',
                    'subject': '1girl',
                    'action': None,
                    'location': None
                }
            },
            'scene_delta': [
                {'location': 'bedroom'},
                {'action': 'standing'},
                {'location': 'kitchen', 'action': 'cooking'}
            ]
        }
        
        config_path = jobs_dir / 'scene_delta_basic.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False)
        
        config = Config(
            job_config_path=str(config_path),
            connection_config_path=str(sample_connection_config)
        )
        
        # prompts が正しくコンパイルされていることを確認
        assert len(config.prompts) == 3
        
        # 1つ目: quality, subject, location（actionはNone）
        assert config.prompts[0].template == "masterpiece, best quality, 1girl, bedroom"
        
        # 2つ目: 前からlocationを継承、actionを追加
        assert config.prompts[1].template == "masterpiece, best quality, 1girl, standing, bedroom"
        
        # 3つ目: locationとactionを上書き
        assert config.prompts[2].template == "masterpiece, best quality, 1girl, cooking, kitchen"
    
    def test_prompts_delta_with_from_base(self, temp_config_dir, sample_connection_config):
        """_from: base でテンプレートにリセットするテスト"""
        jobs_dir = temp_config_dir / 'jobs'
        jobs_dir.mkdir(exist_ok=True)
        
        config_data = {
            'job_name': 'prompts_delta_from_base',
            'job_type': 'sequence',
            'prompt_template': {
                'order': ['quality', 'subject', 'action'],
                'slots': {
                    'quality': 'masterpiece',
                    'subject': '1girl',
                    'action': None
                }
            },
            'scene_delta': [
                {'action': 'running'},
                {'action': 'jumping'},
                {'_from': 'base', 'action': 'sleeping'}  # baseにリセット
            ]
        }
        
        config_path = jobs_dir / 'scene_delta_from_base.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False)
        
        config = Config(
            job_config_path=str(config_path),
            connection_config_path=str(sample_connection_config)
        )
        
        assert len(config.prompts) == 3
        assert config.prompts[0].template == "masterpiece, 1girl, running"
        assert config.prompts[1].template == "masterpiece, 1girl, jumping"
        # 3つ目はbaseからリセットされて、新たにactionだけ追加
        assert config.prompts[2].template == "masterpiece, 1girl, sleeping"
    
    def test_prompts_delta_with_from_id(self, temp_config_dir, sample_connection_config):
        """_from: ID で特定のシーンを参照するテスト"""
        jobs_dir = temp_config_dir / 'jobs'
        jobs_dir.mkdir(exist_ok=True)
        
        config_data = {
            'job_name': 'prompts_delta_from_id',
            'job_type': 'sequence',
            'prompt_template': {
                'order': ['subject', 'action', 'location'],
                'slots': {
                    'subject': '1girl',
                    'action': None,
                    'location': None
                }
            },
            'scene_delta': [
                {'_id': 'scene_a', 'action': 'standing', 'location': 'park'},
                {'action': 'walking'},  # scene_aから継承
                {'_from': 'scene_a', 'location': 'beach'}  # scene_aを参照
            ]
        }
        
        config_path = jobs_dir / 'scene_delta_from_id.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False)
        
        config = Config(
            job_config_path=str(config_path),
            connection_config_path=str(sample_connection_config)
        )
        
        assert len(config.prompts) == 3
        assert config.prompts[0].template == "1girl, standing, park"
        assert config.prompts[1].template == "1girl, walking, park"
        # scene_aから参照（standing, park）してlocationだけ上書き
        assert config.prompts[2].template == "1girl, standing, beach"
    
    def test_prompts_delta_with_unset(self, temp_config_dir, sample_connection_config):
        """_unset でslotを除外するテスト"""
        jobs_dir = temp_config_dir / 'jobs'
        jobs_dir.mkdir(exist_ok=True)
        
        config_data = {
            'job_name': 'prompts_delta_unset',
            'job_type': 'sequence',
            'prompt_template': {
                'order': ['quality', 'subject', 'action'],
                'slots': {
                    'quality': 'masterpiece',
                    'subject': '1girl',
                    'action': 'standing'
                }
            },
            'scene_delta': [
                {},  # そのまま
                {'_unset': ['action']}  # actionを除外
            ]
        }
        
        config_path = jobs_dir / 'scene_delta_unset.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False)
        
        config = Config(
            job_config_path=str(config_path),
            connection_config_path=str(sample_connection_config)
        )
        
        assert len(config.prompts) == 2
        assert config.prompts[0].template == "masterpiece, 1girl, standing"
        assert config.prompts[1].template == "masterpiece, 1girl"
    
    def test_prompts_delta_with_add(self, temp_config_dir, sample_connection_config):
        """_add で配列slotに追加するテスト"""
        jobs_dir = temp_config_dir / 'jobs'
        jobs_dir.mkdir(exist_ok=True)
        
        config_data = {
            'job_name': 'prompts_delta_add',
            'job_type': 'sequence',
            'prompt_template': {
                'order': ['quality', 'subject', 'extra'],
                'slots': {
                    'quality': 'masterpiece',
                    'subject': '1girl',
                    'extra': []
                }
            },
            'scene_delta': [
                {'_add': {'extra': 'blue eyes'}},
                {'_add': {'extra': ['blonde hair', 'smile']}}
            ]
        }
        
        config_path = jobs_dir / 'scene_delta_add.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False)
        
        config = Config(
            job_config_path=str(config_path),
            connection_config_path=str(sample_connection_config)
        )
        
        assert len(config.prompts) == 2
        assert config.prompts[0].template == "masterpiece, 1girl, blue eyes"
        # 2つ目は前から継承して追加
        assert config.prompts[1].template == "masterpiece, 1girl, blue eyes, blonde hair, smile"
    
    def test_prompts_delta_with_tag_array_slot(self, temp_config_dir, sample_connection_config):
        """slotにタグ配列を直接指定するテスト"""
        jobs_dir = temp_config_dir / 'jobs'
        jobs_dir.mkdir(exist_ok=True)
        
        config_data = {
            'job_name': 'prompts_delta_tag_array',
            'job_type': 'sequence',
            'prompt_template': {
                'order': ['quality', 'subject', 'details'],
                'slots': {
                    'quality': 'masterpiece',
                    'subject': '1girl',
                    'details': None
                }
            },
            'scene_delta': [
                {'details': ['blue eyes', 'blonde hair', 'smile']}
            ]
        }
        
        config_path = jobs_dir / 'scene_delta_tag_array.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False)
        
        config = Config(
            job_config_path=str(config_path),
            connection_config_path=str(sample_connection_config)
        )
        
        assert len(config.prompts) == 1
        assert config.prompts[0].template == "masterpiece, 1girl, blue eyes, blonde hair, smile"
    
    def test_prompts_delta_with_runs(self, temp_config_dir, sample_connection_config):
        """_runs でpromptごとのruns指定テスト"""
        jobs_dir = temp_config_dir / 'jobs'
        jobs_dir.mkdir(exist_ok=True)
        
        config_data = {
            'job_name': 'prompts_delta_runs',
            'job_type': 'sequence',
            'prompt_template': {
                'order': ['subject'],
                'slots': {
                    'subject': '1girl'
                }
            },
            'scene_delta': [
                {},
                {'_runs': 3}
            ]
        }
        
        config_path = jobs_dir / 'scene_delta_runs.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False)
        
        config = Config(
            job_config_path=str(config_path),
            connection_config_path=str(sample_connection_config)
        )
        
        assert len(config.prompts) == 2
        assert config.prompts[0].runs is None  # default_runsを使用
        assert config.prompts[1].runs == 3
    
    def test_prompts_delta_error_both_prompts_and_delta(self, temp_config_dir, sample_connection_config):
        """prompts と prompts_delta の両方があるとエラーになるテスト"""
        jobs_dir = temp_config_dir / 'jobs'
        jobs_dir.mkdir(exist_ok=True)
        
        config_data = {
            'job_name': 'prompts_delta_error',
            'job_type': 'sequence',
            'prompts': [
                {'template': 'test', 'runs': 1}
            ],
            'prompt_template': {
                'order': ['subject'],
                'slots': {'subject': '1girl'}
            },
            'scene_delta': [
                {}
            ]
        }
        
        config_path = jobs_dir / 'scene_delta_error.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False)
        
        with pytest.raises(ValueError, match="'prompts' と 'scene_delta' は同時に指定できません"):
            Config(
                job_config_path=str(config_path),
                connection_config_path=str(sample_connection_config)
            )
    
    def test_prompts_delta_error_no_template(self, temp_config_dir, sample_connection_config):
        """prompt_template なしで scene_delta があるとエラーになるテスト"""
        jobs_dir = temp_config_dir / 'jobs'
        jobs_dir.mkdir(exist_ok=True)
        
        config_data = {
            'job_name': 'scene_delta_no_template',
            'job_type': 'sequence',
            'scene_delta': [
                {'action': 'running'}
            ]
        }
        
        config_path = jobs_dir / 'scene_delta_no_template.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False)
        
        with pytest.raises(ValueError, match="'scene_delta' を使用する場合は 'prompt_template' が必須です"):
            Config(
                job_config_path=str(config_path),
                connection_config_path=str(sample_connection_config)
            )
    
    def test_prompts_delta_error_invalid_from_id(self, temp_config_dir, sample_connection_config):
        """_from で存在しないIDを指定するとエラーになるテスト"""
        jobs_dir = temp_config_dir / 'jobs'
        jobs_dir.mkdir(exist_ok=True)
        
        config_data = {
            'job_name': 'prompts_delta_invalid_from',
            'job_type': 'sequence',
            'prompt_template': {
                'order': ['subject'],
                'slots': {'subject': '1girl'}
            },
            'scene_delta': [
                {'_from': 'nonexistent_id'}
            ]
        }
        
        config_path = jobs_dir / 'scene_delta_invalid_from.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False)
        
        with pytest.raises(ValueError, match="_from で参照した ID 'nonexistent_id' は存在しません"):
            Config(
                job_config_path=str(config_path),
                connection_config_path=str(sample_connection_config)
            )

    def test_prompts_delta_raises_use_scene_delta(self, temp_config_dir, sample_connection_config):
        """prompts_delta が指定されているとエラーになり scene_delta の使用を促すテスト"""
        jobs_dir = temp_config_dir / 'jobs'
        jobs_dir.mkdir(exist_ok=True)
        config_data = {
            'job_name': 'prompts_delta_deprecated',
            'job_type': 'sequence',
            'prompt_template': {
                'order': ['subject'],
                'slots': {'subject': '1girl'}
            },
            'prompts_delta': [{}]
        }
        config_path = jobs_dir / 'prompts_delta_deprecated.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False)
        with pytest.raises(ValueError, match="'scene_delta' を使用してください"):
            Config(
                job_config_path=str(config_path),
                connection_config_path=str(sample_connection_config)
            )

    def test_scene_delta_params_inheritance(self, temp_config_dir, sample_connection_config):
        """scene_delta の _params が set→以後継承され、2つ目のシーンにも含まれるテスト"""
        jobs_dir = temp_config_dir / 'jobs'
        jobs_dir.mkdir(exist_ok=True)
        config_data = {
            'job_name': 'scene_delta_params',
            'job_type': 'sequence',
            'prompt_template': {
                'order': ['subject'],
                'slots': {'subject': '1girl'}
            },
            'scene_delta': [
                {
                    'subject': '1girl',
                    '_params': [
                        {'node_id': 10, 'input_name': 'width', 'value': 768},
                        {'node_id': 10, 'input_name': 'height', 'value': 1024}
                    ]
                },
                {'subject': '1boy'}  # _params なし → 1つ目で set した値が継承される
            ]
        }
        config_path = jobs_dir / 'scene_delta_params.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False)
        config = Config(
            job_config_path=str(config_path),
            connection_config_path=str(sample_connection_config)
        )
        assert len(config.prompts) == 2
        # 1つ目: _params を set
        assert config.prompts[0].params is not None
        assert len(config.prompts[0].params) == 2
        keys0 = {(p.node_id, p.input_name) for p in config.prompts[0].params}
        assert (10, 'width') in keys0 and (10, 'height') in keys0
        # 2つ目: _params を省略しても 1つ目で set した値が継承されている
        assert config.prompts[1].params is not None
        assert len(config.prompts[1].params) == 2
        keys1 = {(p.node_id, p.input_name) for p in config.prompts[1].params}
        assert (10, 'width') in keys1 and (10, 'height') in keys1
        # 値の確認
        w0 = next(p for p in config.prompts[0].params if p.input_name == 'width')
        w1 = next(p for p in config.prompts[1].params if p.input_name == 'width')
        assert w0.value == 768 and w1.value == 768

    def test_prompts_delta_with_del(self, temp_config_dir, sample_connection_config):
        """_del でタグを完全一致削除するテスト"""
        jobs_dir = temp_config_dir / 'jobs'
        jobs_dir.mkdir(exist_ok=True)
        config_data = {
            'job_name': 'prompts_delta_del',
            'job_type': 'sequence',
            'prompt_template': {
                'order': ['quality', 'subject', 'extra'],
                'slots': {
                    'quality': 'masterpiece, best quality',
                    'subject': '1girl',
                    'extra': 'blue eyes, blonde hair, smile'
                }
            },
            'scene_delta': [
                {},
                {'_del': {'extra': 'blonde hair'}},
                {'_del': {'extra': ['blue eyes', 'smile']}}
            ]
        }
        config_path = jobs_dir / 'scene_delta_del.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False)
        config = Config(
            job_config_path=str(config_path),
            connection_config_path=str(sample_connection_config)
        )
        assert len(config.prompts) == 3
        assert config.prompts[0].template == "masterpiece, best quality, 1girl, blue eyes, blonde hair, smile"
        assert config.prompts[1].template == "masterpiece, best quality, 1girl, blue eyes, smile"
        assert config.prompts[2].template == "masterpiece, best quality, 1girl"

    def test_prompts_delta_str_slot_normalized_add_del(self, temp_config_dir, sample_connection_config):
        """slotがstrでも正規化され_add/_delが動くテスト"""
        jobs_dir = temp_config_dir / 'jobs'
        jobs_dir.mkdir(exist_ok=True)
        config_data = {
            'job_name': 'scene_delta_str_slot',
            'job_type': 'sequence',
            'prompt_template': {
                'order': ['tags'],
                'slots': {'tags': 'a, b, c'}
            },
            'scene_delta': [
                {'_del': {'tags': 'b'}},
                {'_add': {'tags': 'd'}}
            ]
        }
        config_path = jobs_dir / 'scene_delta_str_slot.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False)
        config = Config(
            job_config_path=str(config_path),
            connection_config_path=str(sample_connection_config)
        )
        assert len(config.prompts) == 2
        assert config.prompts[0].template == "a, c"
        assert config.prompts[1].template == "a, c, d"

    def test_prompts_delta_del_with_constants_expanded(self, temp_config_dir, sample_connection_config):
        """slotが %constant% の場合でも constants 展開後のタグに対して _del が効くテスト"""
        jobs_dir = temp_config_dir / 'jobs'
        jobs_dir.mkdir(exist_ok=True)
        config_data = {
            'job_name': 'prompts_delta_del_constants',
            'job_type': 'sequence',
            'constants': {
                'tags': ['a', 'b', 'c']
            },
            'prompt_template': {
                'order': ['tags'],
                'slots': {
                    'tags': '%tags%'
                }
            },
            'scene_delta': [
                {'_del': {'tags': 'b'}}
            ]
        }
        config_path = jobs_dir / 'scene_delta_del_constants.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False)
        config = Config(
            job_config_path=str(config_path),
            connection_config_path=str(sample_connection_config)
        )
        assert len(config.prompts) == 1
        assert config.prompts[0].template == "a, c"

    def test_constants_accept_list(self, temp_config_dir, sample_connection_config):
        """constants の値が List[str] でも受け付けるテスト"""
        jobs_dir = temp_config_dir / 'jobs'
        jobs_dir.mkdir(exist_ok=True)
        config_data = {
            'job_name': 'constants_list_test',
            'job_type': 'sequence',
            'constants': {
                'tags': ['masterpiece', 'best quality', '1girl']
            },
            'prompts': [
                {'template': '%tags%, standing', 'runs': 1}
            ]
        }
        config_path = jobs_dir / 'constants_list.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False)
        config = Config(
            job_config_path=str(config_path),
            connection_config_path=str(sample_connection_config)
        )
        assert config.constants['tags'] == ['masterpiece', 'best quality', '1girl']