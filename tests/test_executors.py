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
        assert processed_vars[0]['node_id'] == 1
        assert processed_vars[0]['input_name'] == 'test_param'
        assert processed_vars[0]['values'] == ['value1', 'value2']
    
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
        assert processed_vars[0]['node_id'] == 1
        assert processed_vars[0]['input_name'] == 'text'
        
        # 2つのprompt × 2つのcharacter = 4つの値が生成される
        expanded_values = processed_vars[0]['values']
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
        params = executor._build_params(template)
        
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