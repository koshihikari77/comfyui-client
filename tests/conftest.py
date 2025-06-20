"""
ComfyV テスト用の共通設定とフィクスチャ
"""
import pytest
import tempfile
import shutil
import json
import yaml
from pathlib import Path
from unittest.mock import MagicMock

# テスト対象のモジュールをインポート
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))

from core.config import Config
from core.mock_services import MockServiceContainer


@pytest.fixture
def temp_config_dir():
    """一時的な設定ディレクトリを作成"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_job_config(temp_config_dir):
    """テスト用のジョブ設定ファイルを作成"""
    # jobs サブディレクトリを作成してjob設定ファイルを配置
    jobs_dir = temp_config_dir / 'jobs'
    jobs_dir.mkdir()
    
    config_data = {
        'job_name': 'test_job',
        'job_type': 'grid_search',
        'base_workflow': 'workflows/test_workflow.json',
        'variables': [
            {
                'node_id': 1,
                'input_name': 'test_param',
                'values': ['value1', 'value2']
            }
        ]
    }
    
    config_path = jobs_dir / 'test_job.yaml'
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config_data, f, default_flow_style=False)
    
    return config_path


@pytest.fixture
def sample_connection_config(temp_config_dir):
    """テスト用の接続設定ファイルを作成"""
    config_data = {
        'server_address': 'http://localhost:8188'
    }
    
    config_path = temp_config_dir / 'connection.yaml'
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config_data, f, default_flow_style=False)
    
    return config_path


@pytest.fixture
def sample_workflow(temp_config_dir):
    """テスト用のワークフローファイルを作成"""
    # workflows サブディレクトリを作成
    workflows_dir = temp_config_dir / 'workflows'
    workflows_dir.mkdir()
    
    workflow_data = {
        "1": {
            "inputs": {
                "test_param": "default_value"
            },
            "class_type": "TestNode"
        }
    }
    
    workflow_path = workflows_dir / 'test_workflow.json'
    with open(workflow_path, 'w', encoding='utf-8') as f:
        json.dump(workflow_data, f)
    
    return workflow_path


@pytest.fixture
def config_instance(sample_job_config, sample_connection_config, sample_workflow):
    """Configインスタンスを作成（ワークフローファイルが存在することを確保）"""
    return Config(
        job_config_path=str(sample_job_config),
        connection_config_path=str(sample_connection_config)
    )


@pytest.fixture
def mock_service_container():
    """MockServiceContainerインスタンスを作成"""
    return MockServiceContainer()


@pytest.fixture
def sample_sequence_job_config(temp_config_dir):
    """シーケンスジョブ用のテスト設定を作成"""
    # jobs サブディレクトリを作成
    jobs_dir = temp_config_dir / 'jobs'
    jobs_dir.mkdir()
    
    config_data = {
        'job_name': 'test_sequence_job',
        'job_type': 'sequence',
        'prompts': [
            {
                'template': 'test prompt 1',
                'runs': 2
            },
            {
                'template': 'test prompt 2 with __wildcard__',
                'runs': 1
            }
        ]
    }
    
    config_path = jobs_dir / 'test_sequence_job.yaml'
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config_data, f, default_flow_style=False)
    
    return config_path 