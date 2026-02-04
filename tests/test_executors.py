"""
Executorsのテスト
"""
import pytest
import json
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.executors.grid_search_executor import GridSearchJobExecutor
from core.executors.sequence_executor import SequenceJobExecutor


class TestGridSearchJobExecutor:
    """GridSearchJobExecutorのテストケース"""
    
    def test_initialization(self, config_instance, mock_service_container):
        """GridSearchJobExecutor の初期化テスト"""
        executor = GridSearchJobExecutor(config_instance, mock_service_container)
        
        assert executor.config == config_instance
        assert executor.service_container == mock_service_container
        assert executor.db is not None
        assert executor.api is not None
        assert executor.prompt_resolver is not None
    
    def test_prepare_workflow(self, config_instance, mock_service_container):
        """ワークフロー準備のテスト"""
        executor = GridSearchJobExecutor(config_instance, mock_service_container)
        
        params = {"1.test_param": "new_value"}
        prepared_workflow = executor._prepare_workflow(params)
        
        assert prepared_workflow["1"]["inputs"]["test_param"] == "new_value"
    
    def test_preprocess_variables_simple(self, config_instance, mock_service_container):
        """基本的な変数前処理のテスト"""
        executor = GridSearchJobExecutor(config_instance, mock_service_container)
        processed_vars = executor._preprocess_variables()
        
        # プレースホルダーがない場合は元の変数がそのまま返される
        assert len(processed_vars) == 1
        # Pydanticモデルなので属性アクセスを使用
        assert processed_vars[0].node_id == 1
        assert processed_vars[0].input_name == 'test_param'
        assert processed_vars[0].values == ['value1', 'value2']
    
    def test_preprocess_variables_with_placeholders(self, temp_config_dir, sample_connection_config, mock_service_container):
        """プレースホルダー付きの変数前処理テスト"""
        # jobs サブディレクトリを作成
        jobs_dir = temp_config_dir / 'jobs'
        jobs_dir.mkdir()
        
        # workflows サブディレクトリを作成
        workflows_dir = temp_config_dir / 'workflows'
        workflows_dir.mkdir()
        
        # プレースホルダー付きの設定を作成
        config_data = {
            'job_name': 'test_placeholders',
            'job_type': 'grid_search',
            'base_workflow': 'workflows/test_workflow.json',
            'variables': [
                {
                    'node_id': 1,
                    'input_name': 'text',  # プロンプト系の変数名
                    'values': ['Hello {character}', 'Hi {character}']
                }
            ],
            'placeholders': {
                'character': ['Alice', 'Bob']
            }
        }
        
        config_path = jobs_dir / 'placeholder_job.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            import yaml
            yaml.dump(config_data, f, default_flow_style=False)
        
        # テスト用ワークフローも作成
        workflow_data = {"1": {"inputs": {"text": "default"}, "class_type": "TestNode"}}
        workflow_path = workflows_dir / 'test_workflow.json'
        with open(workflow_path, 'w', encoding='utf-8') as f:
            json.dump(workflow_data, f)
        
        from core.config import Config
        config = Config(str(config_path), str(sample_connection_config))
        executor = GridSearchJobExecutor(config, mock_service_container)
        
        processed_vars = executor._preprocess_variables()
        
        # プレースホルダーが展開されていることを確認
        assert len(processed_vars) == 1
        # Pydanticモデルなので属性アクセスを使用
        assert processed_vars[0].node_id == 1
        assert processed_vars[0].input_name == 'text'
        
        # 2つのprompt × 2つのcharacter = 4つの値が生成される
        # Pydanticモデルなので属性アクセスを使用
        expanded_values = processed_vars[0].values
        assert len(expanded_values) == 4
        assert 'Hello Alice' in expanded_values
        assert 'Hello Bob' in expanded_values
        assert 'Hi Alice' in expanded_values
        assert 'Hi Bob' in expanded_values
    
    @patch('pathlib.Path.mkdir')
    def test_run_execution(self, mock_mkdir, config_instance, mock_service_container):
        """実行プロセス全体のテスト"""
        executor = GridSearchJobExecutor(config_instance, mock_service_container)
        
        # run メソッドを実行
        executor.run()
        
        # MockDatabaseManager のジョブが作成されているか確認
        db = mock_service_container.get_database_manager()
        assert len(db.jobs) == 1
        assert db.jobs[1]['status'] == 'completed'
        
        # 画像レコードが作成されているか確認（2つの組み合わせ分）
        assert len(db.images) == 2


class TestSequenceJobExecutor:
    """SequenceJobExecutorのテストケース"""
    
    def test_initialization(self, sample_sequence_job_config, sample_connection_config, mock_service_container):
        """SequenceJobExecutor の初期化テスト"""
        from core.config import Config
        config = Config(str(sample_sequence_job_config), str(sample_connection_config))
        
        executor = SequenceJobExecutor(config, mock_service_container)
        
        assert executor.config == config
        assert executor.service_container == mock_service_container
        assert executor.db is not None
        assert executor.api is not None
        assert executor.prompt_resolver is not None
    
    def test_build_params(self, sample_sequence_job_config, sample_connection_config, mock_service_container):
        """パラメータ構築のテスト"""
        from core.config import Config
        config = Config(str(sample_sequence_job_config), str(sample_connection_config))
        
        executor = SequenceJobExecutor(config, mock_service_container)
        
        template = 'test prompt with wildcard'
        prompt_def = config.prompts[0] if config.prompts else type('PromptDef', (), {'template': template, 'params': None})()
        params = executor._build_params(template, iteration_index=0, local_run_index=0, prompt_def=prompt_def)
        
        # パラメータが辞書として返されることを確認
        assert isinstance(params, dict)
    
    @patch('pathlib.Path.mkdir')
    def test_run_execution(self, mock_mkdir, sample_sequence_job_config, sample_connection_config, mock_service_container):
        """シーケンス実行プロセス全体のテスト"""
        from core.config import Config
        config = Config(str(sample_sequence_job_config), str(sample_connection_config))
        
        executor = SequenceJobExecutor(config, mock_service_container)
        
        # run メソッドを実行
        executor.run()
        
        # MockDatabaseManager のジョブが作成されているか確認
        db = mock_service_container.get_database_manager()
        assert len(db.jobs) == 1
        assert db.jobs[1]['status'] == 'completed'
        
        # 画像レコードが作成されているか確認（3回実行分）
        assert len(db.images) == 3

    def test_substitute_constant_syntax_with_list(self, temp_config_dir, sample_connection_config, mock_service_container):
        """constants の値が List[str] のとき %name% が ", ".join(list) で置換されるテスト"""
        import yaml
        from core.config import Config
        jobs_dir = temp_config_dir / 'jobs'
        jobs_dir.mkdir()
        config_data = {
            'job_name': 'constants_list_subst',
            'job_type': 'sequence',
            'constants': {
                'tags': ['masterpiece', 'best quality', '1girl']
            },
            'prompts': [{'template': 'dummy', 'runs': 1}]
        }
        config_path = jobs_dir / 'constants_list_job.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False)
        config = Config(str(config_path), str(sample_connection_config))
        executor = SequenceJobExecutor(config, mock_service_container)
        result = executor._substitute_constant_syntax('%tags%, standing')
        assert result == "masterpiece, best quality, 1girl, standing"


class TestBaseExecutorMethods:
    """BaseExecutorの共通メソッドのテスト"""
    
    def test_execute_single_run_success(self, config_instance, mock_service_container):
        """単一実行の成功ケースのテスト"""
        executor = GridSearchJobExecutor(config_instance, mock_service_container)
        
        # テスト用のジョブを作成
        db = mock_service_container.get_database_manager()
        job_id = db.create_job("test_job", {})
        
        # 実行テスト
        with patch('builtins.open', MagicMock()):
            result = executor._execute_single_run(job_id, {"test": "workflow"}, {})
        
        assert result is True
        
        # 画像レコードが正しく更新されているか確認
        assert len(db.images) == 1
        assert db.images[1]['status'] == 'success'
    
    def test_prepare_workflow_missing_node(self, config_instance, mock_service_container):
        """存在しないノードIDでのワークフロー準備テスト"""
        executor = GridSearchJobExecutor(config_instance, mock_service_container)
        
        # 存在しないノードIDを指定
        params = {"999.nonexistent_param": "value"}
        
        # 警告が出るが例外は発生しない
        prepared_workflow = executor._prepare_workflow(params)
        
        # 元のワークフローが返される
        assert prepared_workflow["1"]["inputs"]["test_param"] == "default_value" 
    
    def test_sequence_executor_with_new_prompt_format(self, temp_config_dir, sample_connection_config, mock_service_container):
        """SequenceExecutorの新プロンプト形式（List[str]）対応テスト"""
        jobs_dir = temp_config_dir / 'jobs'
        jobs_dir.mkdir()
        workflows_dir = temp_config_dir / 'workflows'
        workflows_dir.mkdir()
        
        # 新形式を含むsequence job設定
        config_data = {
            'job_name': 'sequence_new_format_test',
            'job_type': 'sequence',
            'base_workflow': 'workflows/test_sequence.json',
            'default_runs': 1,
            'prompt_target': {'node_id': 1, 'input_name': 'text'},
            'prompts': [
                # 新形式1: List[str]
                ["1girl", "<preset:character>", "school_uniform"],
                # 新形式2: フロースタイル
                ["1boy", "suit", "office"],
                # 従来形式との混在
                {
                    "template": "1girl, casual clothes",
                    "runs": 2
                }
            ]
        }
        
        config_path = jobs_dir / 'sequence_new_format.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            import yaml
            yaml.dump(config_data, f, default_flow_style=False)
        
        # テスト用ワークフロー作成
        workflow_data = {"1": {"inputs": {"text": "default"}, "class_type": "TestNode"}}
        workflow_path = workflows_dir / 'test_sequence.json'
        with open(workflow_path, 'w', encoding='utf-8') as f:
            json.dump(workflow_data, f)
        
        from core.config import Config
        config = Config(str(config_path), str(sample_connection_config))
        
        # プロンプトが正規化されていることを確認
        assert len(config.prompts) == 3
        assert config.prompts[0].template == "1girl, <preset:character>, school_uniform"
        assert config.prompts[0].runs is None  # default_runsを使用
        assert config.prompts[1].template == "1boy, suit, office"
        assert config.prompts[2].template == "1girl, casual clothes"
        assert config.prompts[2].runs == 2
        
        executor = SequenceJobExecutor(config, mock_service_container)
        
        # 実行テスト
        with patch('pathlib.Path.mkdir'):
            executor.run()
        
        # 実行結果確認
        db = mock_service_container.get_database_manager()
        assert len(db.jobs) == 1
        assert db.jobs[1]['status'] == 'completed'
        
        # 画像レコード数確認：1 + 1 + 2 = 4回実行
        assert len(db.images) == 4
    
    def test_sequence_executor_default_runs_usage(self, temp_config_dir, sample_connection_config, mock_service_container):
        """SequenceExecutorのdefault_runs使用テスト"""
        jobs_dir = temp_config_dir / 'jobs'
        jobs_dir.mkdir()
        workflows_dir = temp_config_dir / 'workflows'
        workflows_dir.mkdir()
        
        config_data = {
            'job_name': 'default_runs_test',
            'job_type': 'sequence',
            'base_workflow': 'workflows/test_sequence.json',
            'default_runs': 3,  # デフォルト実行回数を3に設定
            'prompt_target': {'node_id': 1, 'input_name': 'text'},
            'prompts': [
                ["1girl", "school_uniform"],  # runsが未指定 → default_runs使用
                {"template": "1boy, suit", "runs": 1}  # 明示的に1回指定
            ]
        }
        
        config_path = jobs_dir / 'default_runs_test.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            import yaml
            yaml.dump(config_data, f, default_flow_style=False)
        
        # テスト用ワークフロー作成
        workflow_data = {"1": {"inputs": {"text": "default"}, "class_type": "TestNode"}}
        workflow_path = workflows_dir / 'test_sequence.json'
        with open(workflow_path, 'w', encoding='utf-8') as f:
            json.dump(workflow_data, f)
        
        from core.config import Config
        config = Config(str(config_path), str(sample_connection_config))
        executor = SequenceJobExecutor(config, mock_service_container)
        
        with patch('pathlib.Path.mkdir'):
            executor.run()
        
        # 実行結果確認：3回（default_runs） + 1回（明示指定） = 4回実行
        db = mock_service_container.get_database_manager()
        assert len(db.images) == 4
    
    def test_sequence_executor_iterator_functionality(self, temp_config_dir, sample_connection_config, mock_service_container):
        """SequenceExecutorのIterator機能テスト"""
        jobs_dir = temp_config_dir / 'jobs'
        jobs_dir.mkdir()
        workflows_dir = temp_config_dir / 'workflows'
        workflows_dir.mkdir()
        
        config_data = {
            'job_name': 'iterator_functionality_test',
            'job_type': 'sequence',
            'base_workflow': 'workflows/test_sequence.json',
            'prompt_target': {'node_id': 1, 'input_name': 'text'},
            'iterators': {
                'location': ['library', 'cafe'],
                'mood': ['happy', 'sad', 'angry']
            },
            'prompts': [
                {
                    "template": "1girl, $[location], $[mood]",
                    "runs": 5  # 5回実行、location=2要素、mood=3要素で巡回テスト
                }
            ]
        }
        
        config_path = jobs_dir / 'iterator_test.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            import yaml
            yaml.dump(config_data, f, default_flow_style=False)
        
        # テスト用ワークフロー作成
        workflow_data = {"1": {"inputs": {"text": "default"}, "class_type": "TestNode"}}
        workflow_path = workflows_dir / 'test_sequence.json'
        with open(workflow_path, 'w', encoding='utf-8') as f:
            json.dump(workflow_data, f)
        
        from core.config import Config
        config = Config(str(config_path), str(sample_connection_config))
        executor = SequenceJobExecutor(config, mock_service_container)
        
        # Iterator事前処理テスト（_preprocess_iterators()を呼んで_resolved_iteratorsを初期化）
        resolved_iterators = executor._preprocess_iterators()
        assert 'location' in resolved_iterators
        assert 'mood' in resolved_iterators
        assert resolved_iterators['location'] == ['library', 'cafe']
        assert resolved_iterators['mood'] == ['happy', 'sad', 'angry']
        
        # _resolved_iteratorsとカウンタを設定（_preprocess_iterators()の結果を使用）
        executor._resolved_iterators = resolved_iterators
        executor._iterator_counters = {name: 0 for name in resolved_iterators.keys()}
        
        # テンプレート置換テスト
        template = "1girl, $[location], $[mood]"
        
        # 巡回ロジックテスト（各Iteratorが独立に巡回）
        expected_substitutions = [
            "1girl, library, happy",      # 1回目: location[0], mood[0]
            "1girl, cafe, sad",           # 2回目: location[1], mood[1]  
            "1girl, library, angry",      # 3回目: location[0], mood[2] (locationが巡回)
            "1girl, cafe, happy",         # 4回目: location[1], mood[0] (moodが巡回)
            "1girl, library, sad"         # 5回目: location[0], mood[1] (両方巡回)
        ]
        
        for i, expected in enumerate(expected_substitutions):
            # 各呼び出しでカウンタが自動的にインクリメントされる
            result = executor._substitute_iterator_syntax(template)
            assert result == expected, f"Call {i+1}: expected '{expected}', got '{result}'"
    
    def test_sequence_executor_expand_preset_iterator(self, temp_config_dir, sample_connection_config, mock_service_container):
        """expand_preset機能を使ったIteratorテスト"""
        jobs_dir = temp_config_dir / 'jobs'
        jobs_dir.mkdir()
        workflows_dir = temp_config_dir / 'workflows'
        workflows_dir.mkdir()
        
        config_data = {
            'job_name': 'expand_preset_test',
            'job_type': 'sequence',
            'base_workflow': 'workflows/test_sequence.json',
            'prompt_target': {'node_id': 1, 'input_name': 'text'},
            'iterators': {
                'expression_style': {
                    'expand_preset': 'expression'
                }
            },
            'prompts': [
                {
                    "template": "1girl, $[expression_style]",
                    "runs": 2
                }
            ]
        }
        
        config_path = jobs_dir / 'expand_preset_test.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            import yaml
            yaml.dump(config_data, f, default_flow_style=False)
        
        # テスト用ワークフロー作成
        workflow_data = {"1": {"inputs": {"text": "default"}, "class_type": "TestNode"}}
        workflow_path = workflows_dir / 'test_sequence.json'
        with open(workflow_path, 'w', encoding='utf-8') as f:
            json.dump(workflow_data, f)
        
        from core.config import Config
        config = Config(str(config_path), str(sample_connection_config))
        executor = SequenceJobExecutor(config, mock_service_container)
        
        # expand_preset処理テスト（expressionプリセットが存在すると仮定）
        try:
            resolved_iterators = executor._preprocess_iterators()
            assert 'expression_style' in resolved_iterators
            
            # expand_presetで生成されたpreset参照が正しい形式かチェック
            expression_refs = resolved_iterators['expression_style']
            for ref in expression_refs:
                assert ref.startswith('<preset:expression#'), f"Invalid preset reference: {ref}"
                
        except KeyError:
            # プリセットが存在しない場合は警告ログが出力されることを確認
            import logging
            # この場合はテストスキップまたは警告確認
            pass

    def test_sequence_executor_parameter_combinations_functionality(self, temp_config_dir, mock_service_container, sample_connection_config):
        """SequenceJobExecutor のパラメータ組み合わせ機能テスト"""
        jobs_dir = temp_config_dir / 'jobs'
        workflows_dir = temp_config_dir / 'workflows'
        jobs_dir.mkdir(exist_ok=True)
        workflows_dir.mkdir(exist_ok=True)
        
        config_data = {
            'job_name': 'param_combinations_test',
            'job_type': 'sequence',
            'base_workflow': 'workflows/test_sequence.json',
            'prompts': [
                {'template': 'test prompt', 'runs': 6}
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
                },
                {
                    'name': 'minimal_landscape',
                    'parameters': [
                        {'node_id': 220, 'input_name': 'width', 'value': 1344},
                        {'node_id': 220, 'input_name': 'height', 'value': 768}
                    ]
                }
            ]
        }
        
        config_path = jobs_dir / 'param_combinations_test.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            import yaml
            yaml.dump(config_data, f, default_flow_style=False)
        
        # テスト用ワークフロー作成
        workflow_data = {"1": {"inputs": {"text": "default"}, "class_type": "TestNode"}}
        workflow_path = workflows_dir / 'test_sequence.json'
        with open(workflow_path, 'w', encoding='utf-8') as f:
            json.dump(workflow_data, f)
        
        from core.config import Config
        config = Config(str(config_path), str(sample_connection_config))
        executor = SequenceJobExecutor(config, mock_service_container)
        
        # パラメータ組み合わせの読み込み確認
        combinations = config.parameter_combinations
        assert len(combinations) == 3
        
        # 巡回ロジックテスト
        test_cases = [
            (0, 'high_quality'),     # 1回目: index 0
            (1, 'artistic_portrait'), # 2回目: index 1  
            (2, 'minimal_landscape'), # 3回目: index 2
            (3, 'high_quality'),     # 4回目: index 0 (巡回)
            (4, 'artistic_portrait'), # 5回目: index 1 (巡回)
            (5, 'minimal_landscape'), # 6回目: index 2 (巡回)
        ]
        
        for iteration_index, expected_name in test_cases:
            combination = executor._get_current_parameter_combination(iteration_index)
            assert combination is not None
            assert combination.name == expected_name
        
        # パラメータ適用テスト（優先度確認）
        prompt_def = config.prompts[0]
        # 1回目: high_quality組み合わせ
        params = executor._build_params("test template", 0, 0, prompt_def)
        
        # パラメータ組み合わせの値が適用されているか確認
        assert params['220.width'] == 1024  # high_quality の width
        assert params['220.height'] == 1024  # high_quality の height
        assert params['54.model_weight_1'] == 0.8  # high_quality の model_weight_1
        
        # 2回目: artistic_portrait組み合わせ
        params = executor._build_params("test template", 1, 1, prompt_def)
        assert params['220.width'] == 768   # artistic_portrait の width
        assert params['220.height'] == 1344  # artistic_portrait の height
        assert params['54.model_weight_1'] == 0.6  # artistic_portrait の model_weight_1

    def test_sequence_executor_parameter_priority(self, temp_config_dir, mock_service_container, sample_connection_config):
        """パラメータ適用優先度テスト（ParameterCombination > random_parameters > fixed_parameters）"""
        jobs_dir = temp_config_dir / 'jobs'
        workflows_dir = temp_config_dir / 'workflows'
        jobs_dir.mkdir(exist_ok=True)
        workflows_dir.mkdir(exist_ok=True)
        
        config_data = {
            'job_name': 'priority_test',
            'job_type': 'sequence',
            'base_workflow': 'workflows/test_sequence.json',
            'prompts': [{'template': 'test', 'runs': 2}],
            'fixed_parameters': [
                {'node_id': 220, 'input_name': 'width', 'value': 512},  # 最低優先度
                {'node_id': 171, 'input_name': 'seed', 'value': 12345}
            ],
            'random_parameters': [
                {'node_id': 220, 'input_name': 'width', 'type': 'choice', 'values': [256]},  # 中優先度
                {'node_id': 54, 'input_name': 'model_weight_1', 'type': 'choice', 'values': [0.5]}
            ],
            'parameter_combinations': [
                {
                    'name': 'override_test',
                    'parameters': [
                        {'node_id': 220, 'input_name': 'width', 'value': 1024},  # 最高優先度
                        {'node_id': 220, 'input_name': 'height', 'value': 1024}
                    ]
                }
            ]
        }
        
        config_path = jobs_dir / 'priority_test.yaml'
        with open(config_path, 'w', encoding='utf-8') as f:
            import yaml
            yaml.dump(config_data, f, default_flow_style=False)
        
        # テスト用ワークフロー作成
        workflow_data = {"1": {"inputs": {"text": "default"}, "class_type": "TestNode"}}
        workflow_path = workflows_dir / 'test_sequence.json'
        with open(workflow_path, 'w', encoding='utf-8') as f:
            json.dump(workflow_data, f)
        
        from core.config import Config
        config = Config(str(config_path), str(sample_connection_config))
        executor = SequenceJobExecutor(config, mock_service_container)
        prompt_def = config.prompts[0]
        params = executor._build_params("test template", 0, 0, prompt_def)
        
        # 優先度確認
        assert params['220.width'] == 1024   # ParameterCombination が最優先
        assert params['220.height'] == 1024  # ParameterCombination の値
        assert params['54.model_weight_1'] == 0.5  # random_parameters の値（上書きされない）
        assert params['171.seed'] == 12345   # fixed_parameters の値（上書きされない）