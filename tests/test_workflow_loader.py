"""
WorkflowLoaderクラスのテスト
"""
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from core.workflow_loader import WorkflowLoader
from core.executors.base_executor import BaseExecutor


class TestWorkflowLoader:
    """WorkflowLoaderクラスのテストケース"""
    
    @pytest.fixture
    def sample_workflow_data(self):
        """テスト用のワークフローデータ"""
        return {
            "8": {
                "inputs": {
                    "samples": ["171", 0],
                    "vae": ["138", 2]
                },
                "class_type": "VAEDecode",
                "_meta": {
                    "title": "VAEデコード"
                }
            },
            "30": {
                "inputs": {
                    "width": 4096,
                    "height": 4096,
                    "text_g": ["149", 0],
                    "text_l": ["149", 0],
                    "clip": ["55", 1]
                },
                "class_type": "CLIPTextEncodeSDXL",
                "_meta": {
                    "title": "CLIPテキストエンコードSDXL"
                }
            },
            "149": {
                "inputs": {
                    "text": "test prompt"
                },
                "class_type": "ttN text",
                "_meta": {
                    "title": "text"
                }
            },
            "138": {
                "inputs": {
                    "ckpt_name": "test_model.safetensors"
                },
                "class_type": "CheckpointLoaderSimple",
                "_meta": {
                    "title": "チェックポイントを読み込む"
                }
            },
            "999": {
                "inputs": {
                    "value": 1.0
                },
                "class_type": "NoMetaNode"
                # _metaフィールドなし
            }
        }
    
    @pytest.fixture
    def temp_workflow_file(self, sample_workflow_data):
        """一時的なワークフローファイルを作成"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_workflow_data, f, ensure_ascii=False, indent=2)
            temp_path = Path(f.name)
        
        yield temp_path
        
        # クリーンアップ
        if temp_path.exists():
            temp_path.unlink()
    
    def test_workflow_loader_initialization(self, temp_workflow_file):
        """WorkflowLoaderの初期化テスト"""
        loader = WorkflowLoader(temp_workflow_file)
        
        assert loader.workflow_path == temp_workflow_file
        assert loader._workflow_data is None
        assert loader._node_name_mapping is None
        assert loader._node_id_mapping is None
    
    def test_load_workflow_success(self, temp_workflow_file, sample_workflow_data):
        """ワークフロー読み込み成功テスト"""
        loader = WorkflowLoader(temp_workflow_file)
        workflow_data = loader.load_workflow()
        
        assert workflow_data == sample_workflow_data
        assert loader._workflow_data is not None
        assert loader._node_name_mapping is not None
        assert loader._node_id_mapping is not None
    
    def test_load_workflow_file_not_found(self):
        """存在しないファイルの読み込みテスト"""
        non_existent_path = Path("non_existent_workflow.json")
        loader = WorkflowLoader(non_existent_path)
        
        with pytest.raises(FileNotFoundError) as exc_info:
            loader.load_workflow()
        
        assert "Workflow file not found" in str(exc_info.value)
    
    def test_load_workflow_invalid_json(self):
        """不正なJSONファイルの読み込みテスト"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content {")
            temp_path = Path(f.name)
        
        try:
            loader = WorkflowLoader(temp_path)
            with pytest.raises(json.JSONDecodeError):
                loader.load_workflow()
        finally:
            if temp_path.exists():
                temp_path.unlink()
    
    def test_node_mapping_creation(self, temp_workflow_file):
        """ノードマッピング作成テスト"""
        loader = WorkflowLoader(temp_workflow_file)
        loader.load_workflow()
        
        name_mapping = loader.get_node_mapping()
        id_mapping = loader.get_node_id_mapping()
        
        # 期待されるマッピング
        expected_name_mapping = {
            "VAEデコード": "8",
            "CLIPテキストエンコードSDXL": "30", 
            "text": "149",
            "チェックポイントを読み込む": "138",
            "NoMetaNode": "999"  # class_typeをフォールバックとして使用
        }
        
        assert name_mapping == expected_name_mapping
        
        # 逆マッピングの確認
        for name, node_id in expected_name_mapping.items():
            assert id_mapping[node_id] == name
    
    def test_resolve_node_reference_by_name(self, temp_workflow_file):
        """ノード名による参照解決テスト"""
        loader = WorkflowLoader(temp_workflow_file)
        loader.load_workflow()
        
        # 名前による解決
        assert loader.resolve_node_reference("VAEデコード") == "8"
        assert loader.resolve_node_reference("CLIPテキストエンコードSDXL") == "30"
        assert loader.resolve_node_reference("text") == "149"
        assert loader.resolve_node_reference("チェックポイントを読み込む") == "138"
        assert loader.resolve_node_reference("NoMetaNode") == "999"
    
    def test_resolve_node_reference_by_id(self, temp_workflow_file):
        """ノードIDによる参照解決テスト"""
        loader = WorkflowLoader(temp_workflow_file)
        loader.load_workflow()
        
        # IDによる解決（そのまま返る）
        assert loader.resolve_node_reference("8") == "8"
        assert loader.resolve_node_reference("30") == "30"
        assert loader.resolve_node_reference("149") == "149"
        assert loader.resolve_node_reference("138") == "138"
        assert loader.resolve_node_reference("999") == "999"
    
    def test_resolve_node_reference_not_found(self, temp_workflow_file):
        """存在しないノード参照のテスト"""
        loader = WorkflowLoader(temp_workflow_file)
        loader.load_workflow()
        
        with pytest.raises(ValueError) as exc_info:
            loader.resolve_node_reference("非存在ノード")
        
        assert "Node '非存在ノード' not found" in str(exc_info.value)
        assert "Available names:" in str(exc_info.value)
        assert "Available IDs:" in str(exc_info.value)
    
    def test_get_node_info(self, temp_workflow_file):
        """ノード情報取得テスト"""
        loader = WorkflowLoader(temp_workflow_file)
        loader.load_workflow()
        
        # 名前による情報取得
        info = loader.get_node_info("VAEデコード")
        expected_info = {
            'id': '8',
            'name': 'VAEデコード',
            'class_type': 'VAEDecode',
            'inputs': ['samples', 'vae'],
            'meta': {'title': 'VAEデコード'}
        }
        assert info == expected_info
        
        # IDによる情報取得
        info = loader.get_node_info("30")
        assert info['id'] == '30'
        assert info['name'] == 'CLIPテキストエンコードSDXL'
        assert info['class_type'] == 'CLIPTextEncodeSDXL'
        assert 'width' in info['inputs']
        assert 'height' in info['inputs']
        assert 'text_g' in info['inputs']
    
    def test_list_nodes(self, temp_workflow_file):
        """ノード一覧取得テスト"""
        loader = WorkflowLoader(temp_workflow_file)
        loader.load_workflow()
        
        nodes = loader.list_nodes()
        
        # ソートされた一覧が返される
        expected_nodes = [
            ("8", "VAEデコード", "VAEDecode"),
            ("30", "CLIPテキストエンコードSDXL", "CLIPTextEncodeSDXL"),
            ("138", "チェックポイントを読み込む", "CheckpointLoaderSimple"),
            ("149", "text", "ttN text"),
            ("999", "NoMetaNode", "NoMetaNode")
        ]
        
        assert nodes == expected_nodes
    
    def test_validate_references(self, temp_workflow_file):
        """参照検証テスト"""
        loader = WorkflowLoader(temp_workflow_file)
        loader.load_workflow()
        
        references = [
            "VAEデコード",
            "8",
            "非存在ノード",
            "999",
            "text",
            "存在しないID"
        ]
        
        results = loader.validate_references(references)
        
        expected_results = {
            "VAEデコード": True,
            "8": True,
            "非存在ノード": False,
            "999": True,
            "text": True,
            "存在しないID": False
        }
        
        assert results == expected_results
    
    def test_duplicate_node_names_warning(self):
        """重複するノード名の警告テスト"""
        # 重複する名前を持つワークフローデータ
        duplicate_workflow_data = {
            "1": {
                "class_type": "TestNode1",
                "_meta": {"title": "同じ名前"}
            },
            "2": {
                "class_type": "TestNode2", 
                "_meta": {"title": "同じ名前"}
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(duplicate_workflow_data, f)
            temp_path = Path(f.name)
        
        try:
            loader = WorkflowLoader(temp_path)
            
            with patch('core.workflow_loader.logger') as mock_logger:
                loader.load_workflow()
                
                # 重複警告が記録されることを確認
                mock_logger.warning.assert_called()
                warning_calls = [call.args[0] for call in mock_logger.warning.call_args_list]
                duplicate_warnings = [msg for msg in warning_calls if "Duplicate node name" in msg]
                assert len(duplicate_warnings) > 0
                
        finally:
            if temp_path.exists():
                temp_path.unlink()


class TestBaseExecutorIntegration:
    """BaseExecutorとWorkflowLoaderの統合テスト"""
    
    @pytest.fixture
    def mock_config(self, temp_workflow_file):
        """モック設定"""
        config = Mock()
        config.base_workflow_path = temp_workflow_file
        config.job_name = "test_job"
        config.variables = []
        return config
    
    @pytest.fixture  
    def mock_service_container(self):
        """モックサービスコンテナ"""
        container = Mock()
        container.get_database_manager.return_value = Mock()
        container.get_api_client.return_value = Mock()
        container.get_prompt_resolver.return_value = Mock()
        return container
    
    @pytest.fixture
    def temp_workflow_file(self):
        """テスト用ワークフローファイル"""
        workflow_data = {
            "8": {
                "inputs": {"samples": ["171", 0], "vae": ["138", 2]},
                "class_type": "VAEDecode",
                "_meta": {"title": "VAEデコード"}
            },
            "149": {
                "inputs": {"text": "default"},
                "class_type": "ttN text", 
                "_meta": {"title": "text"}
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(workflow_data, f, ensure_ascii=False)
            temp_path = Path(f.name)
        
        yield temp_path
        
        if temp_path.exists():
            temp_path.unlink()
    
    def test_base_executor_workflow_loader_initialization(self, mock_config, mock_service_container):
        """BaseExecutorでのWorkflowLoader初期化テスト"""
        # BaseExecutor のテスト用サブクラス
        class TestExecutor(BaseExecutor):
            def run(self):
                pass
        
        with patch('core.executors.base_executor.Path.mkdir'):
            executor = TestExecutor(mock_config, mock_service_container)
            
            assert executor.workflow_loader is not None
            assert executor.workflow_loader.workflow_path == mock_config.base_workflow_path
            assert executor.base_workflow is not None
    
    def test_resolve_node_parameter_with_name(self, mock_config, mock_service_container):
        """ノード名を使ったパラメータ解決テスト"""
        class TestExecutor(BaseExecutor):
            def run(self):
                pass
        
        with patch('core.executors.base_executor.Path.mkdir'):
            executor = TestExecutor(mock_config, mock_service_container)
            
            # ノード名による解決
            node_id, input_name = executor._resolve_node_parameter("VAEデコード.samples")
            assert node_id == "8"
            assert input_name == "samples"
            
            # ノード名による解決
            node_id, input_name = executor._resolve_node_parameter("text.text")
            assert node_id == "149"
            assert input_name == "text"
    
    def test_resolve_node_parameter_with_id(self, mock_config, mock_service_container):
        """ノードIDを使ったパラメータ解決テスト"""
        class TestExecutor(BaseExecutor):
            def run(self):
                pass
        
        with patch('core.executors.base_executor.Path.mkdir'):
            executor = TestExecutor(mock_config, mock_service_container)
            
            # IDによる解決（従来通り）
            node_id, input_name = executor._resolve_node_parameter("8.samples")
            assert node_id == "8"
            assert input_name == "samples"
            
            node_id, input_name = executor._resolve_node_parameter("149.text")
            assert node_id == "149"
            assert input_name == "text"
    
    def test_prepare_workflow_with_node_names(self, mock_config, mock_service_container):
        """ノード名を使ったワークフロー準備テスト"""
        class TestExecutor(BaseExecutor):
            def run(self):
                pass
        
        with patch('core.executors.base_executor.Path.mkdir'):
            executor = TestExecutor(mock_config, mock_service_container)
            
            # ノード名とIDが混在するパラメータ
            params = {
                "VAEデコード.samples": ["new_samples", 0],
                "149.text": "new text content", 
                "text.text": "another text"  # 同じノードの異なる指定方法
            }
            
            workflow = executor._prepare_workflow(params)
            
            # VAEデコードノード（ID: 8）の更新確認
            assert workflow["8"]["inputs"]["samples"] == ["new_samples", 0]
            
            # textノード（ID: 149）の更新確認（最後に適用された値）
            assert workflow["149"]["inputs"]["text"] == "another text"
    
    def test_get_workflow_node_info(self, mock_config, mock_service_container):
        """ワークフローノード情報取得テスト"""
        class TestExecutor(BaseExecutor):
            def run(self):
                pass
        
        with patch('core.executors.base_executor.Path.mkdir'):
            executor = TestExecutor(mock_config, mock_service_container)
            
            # ノード名による情報取得
            info = executor.get_workflow_node_info("VAEデコード")
            assert info['id'] == '8'
            assert info['name'] == 'VAEデコード'
            assert info['class_type'] == 'VAEDecode'
            
            # IDによる情報取得
            info = executor.get_workflow_node_info("149")
            assert info['id'] == '149'
            assert info['name'] == 'text'
            assert info['class_type'] == 'ttN text'
    
    def test_list_workflow_nodes(self, mock_config, mock_service_container):
        """ワークフローノード一覧取得テスト"""
        class TestExecutor(BaseExecutor):
            def run(self):
                pass
        
        with patch('core.executors.base_executor.Path.mkdir'):
            executor = TestExecutor(mock_config, mock_service_container)
            
            nodes = executor.list_workflow_nodes()
            
            expected_nodes = [
                ("8", "VAEデコード", "VAEDecode"),
                ("149", "text", "ttN text")
            ]
            
            assert nodes == expected_nodes
    
    def test_validate_parameter_references(self, mock_config, mock_service_container):
        """パラメータ参照検証テスト"""
        class TestExecutor(BaseExecutor):
            def run(self):
                pass
        
        with patch('core.executors.base_executor.Path.mkdir'):
            executor = TestExecutor(mock_config, mock_service_container)
            
            param_keys = [
                "VAEデコード.samples",
                "text.text", 
                "8.vae",
                "149.text",
                "非存在ノード.input",
                "invalid_format"
            ]
            
            results = executor.validate_parameter_references(param_keys)
            
            expected_results = {
                "VAEデコード.samples": True,
                "text.text": True,
                "8.vae": True,
                "149.text": True,
                "非存在ノード.input": False,
                "invalid_format": False
            }
            
            assert results == expected_results