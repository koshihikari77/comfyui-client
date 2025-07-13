"""
main.py の統合テスト
実際のコマンドライン引数を使用したエンドツーエンドのテスト
"""
import pytest
import tempfile
import subprocess
import sys
import json
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock


@pytest.fixture
def integration_temp_dir():
    """統合テスト用の一時ディレクトリを作成"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    import shutil
    shutil.rmtree(temp_dir)


@pytest.fixture
def integration_job_config(integration_temp_dir):
    """統合テスト用のジョブ設定を作成"""
    config_data = {
        'job_name': 'integration_test_job',
        'job_type': 'grid_search',
        'base_workflow': 'test_workflow.json',
        'variables': [
            {
                'node_id': 1,
                'input_name': 'test_param',
                'values': ['value1', 'value2']
            }
        ]
    }
    
    config_path = integration_temp_dir / 'job_config.yaml'
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config_data, f, default_flow_style=False)
    
    # ワークフローファイルも作成
    workflow_data = {
        "1": {
            "inputs": {"test_param": "default_value"},
            "class_type": "TestNode"
        }
    }
    workflow_path = integration_temp_dir / 'test_workflow.json'
    with open(workflow_path, 'w', encoding='utf-8') as f:
        json.dump(workflow_data, f)
    
    return config_path


@pytest.fixture
def integration_connection_config(integration_temp_dir):
    """統合テスト用の接続設定を作成"""
    config_data = {
        'server_address': 'http://localhost:8188'
    }
    
    config_path = integration_temp_dir / 'connection_config.yaml'
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config_data, f, default_flow_style=False)
    
    return config_path


class TestMainIntegration:
    """main.py の統合テスト"""
    
    def test_main_grid_search_test_mode(self, integration_job_config, integration_connection_config):
        """グリッドサーチモードでのテストモード実行"""
        # main.py のパスを取得
        main_path = Path(__file__).resolve().parent.parent.parent / 'main.py'
        
        # コマンドライン引数を構成
        cmd = [
            sys.executable, str(main_path),
            '--job-config', str(integration_job_config),
            '--connection-config', str(integration_connection_config),
            '--test-mode',
            '--verbose'
        ]
        
        # プロセスを実行
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=main_path.parent)
        
        # 成功することを確認
        assert result.returncode == 0, f"Process failed with stderr: {result.stderr}"
        
        # ログメッセージを確認（loggingはstderrに出力される）
        output = result.stderr
        assert "Running in TEST MODE with mock services" in output
        assert "Verification job completed successfully!" in output
    
    def test_main_sequence_mode(self, integration_temp_dir, integration_connection_config):
        """シーケンスモードでの実行テスト"""
        # シーケンスジョブ設定を作成
        sequence_config_data = {
            'job_name': 'integration_sequence_test',
            'job_type': 'sequence',
            'prompts': [
                {
                    'template': 'test prompt 1',
                    'runs': 1
                },
                {
                    'template': 'test prompt 2',
                    'runs': 1
                }
            ]
        }
        
        sequence_config_path = integration_temp_dir / 'sequence_config.yaml'
        with open(sequence_config_path, 'w', encoding='utf-8') as f:
            yaml.dump(sequence_config_data, f, default_flow_style=False)
        
        main_path = Path(__file__).resolve().parent.parent.parent / 'main.py'
        
        cmd = [
            sys.executable, str(main_path),
            '--job-config', str(sequence_config_path),
            '--connection-config', str(integration_connection_config),
            '--test-mode'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=main_path.parent)
        
        assert result.returncode == 0, f"Process failed with stderr: {result.stderr}"
        output = result.stderr
        assert "Verification job completed successfully!" in output
    
    def test_main_missing_job_config(self, integration_connection_config):
        """ジョブ設定ファイルが存在しない場合のエラーハンドリング"""
        main_path = Path(__file__).resolve().parent.parent.parent / 'main.py'
        
        cmd = [
            sys.executable, str(main_path),
            '--job-config', 'nonexistent_job.yaml',
            '--connection-config', str(integration_connection_config),
            '--test-mode'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=main_path.parent)
        
        # ファイルが見つからないエラーで終了することを確認
        assert result.returncode != 0
        assert "Job config file not found" in result.stderr
    
    def test_main_invalid_job_type(self, integration_temp_dir, integration_connection_config):
        """無効なジョブタイプでのエラーハンドリング"""
        # 無効なジョブタイプの設定を作成
        invalid_config_data = {
            'job_name': 'invalid_job_type_test',
            'job_type': 'invalid_type',  # 存在しないタイプ
            'base_workflow': 'test.json',
            'variables': []
        }
        
        invalid_config_path = integration_temp_dir / 'invalid_job_type.yaml'
        with open(invalid_config_path, 'w', encoding='utf-8') as f:
            yaml.dump(invalid_config_data, f, default_flow_style=False)
        
        main_path = Path(__file__).resolve().parent.parent.parent / 'main.py'
        
        cmd = [
            sys.executable, str(main_path),
            '--job-config', str(invalid_config_path),
            '--connection-config', str(integration_connection_config),
            '--test-mode'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=main_path.parent)
        
        # 無効なジョブタイプエラーで終了することを確認
        assert result.returncode != 0
        assert "Input should be 'grid_search' or 'sequence'" in result.stderr
    
    def test_command_line_argument_parsing(self):
        """コマンドライン引数の解析テスト"""
        main_path = Path(__file__).resolve().parent.parent.parent / 'main.py'
        
        # ヘルプオプションのテスト
        cmd = [sys.executable, str(main_path), '--help']
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=main_path.parent)
        
        assert result.returncode == 0
        assert "ComfyV Verification Framework" in result.stdout
        assert "--job-config" in result.stdout
        assert "--connection-config" in result.stdout
        assert "--verbose" in result.stdout
        assert "--test-mode" in result.stdout
    
    def test_verbose_logging(self, integration_job_config, integration_connection_config):
        """詳細ログ出力のテスト"""
        main_path = Path(__file__).resolve().parent.parent.parent / 'main.py'
        
        # 詳細ログ有効で実行
        cmd = [
            sys.executable, str(main_path),
            '--job-config', str(integration_job_config),
            '--connection-config', str(integration_connection_config),
            '--test-mode',
            '--verbose'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=main_path.parent)
        
        assert result.returncode == 0
        # DEBUGレベルのログが出力されていることを確認
        output = result.stderr
        assert "DEBUG" in output 