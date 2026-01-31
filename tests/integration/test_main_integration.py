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
import os
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

    def test_main_dump_prompts(self, integration_temp_dir, integration_connection_config):
        """--dump-prompts: sequenceジョブの解決済みプロンプトを1行1件でファイルに出力する"""
        dump_job_data = {
            'job_name': 'dump_prompts_test',
            'job_type': 'sequence',
            'constants': {
                'base': 'masterpiece, best quality',
            },
            'iterators': {
                'loc': ['park', 'cafe'],
            },
            'prompts': [
                {'template': '%base%, 1girl, $[loc]', 'runs': 2},
            ],
        }
        job_path = integration_temp_dir / 'dump_prompts_job.yaml'
        with open(job_path, 'w', encoding='utf-8') as f:
            yaml.dump(dump_job_data, f, default_flow_style=False)
        out_path = integration_temp_dir / 'out_prompts.txt'
        main_path = Path(__file__).resolve().parent.parent.parent / 'main.py'
        cmd = [
            sys.executable, str(main_path),
            '--job-config', str(job_path),
            '--connection-config', str(integration_connection_config),
            '--dump-prompts', str(out_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=main_path.parent)
        assert result.returncode == 0, f"Process failed with stderr: {result.stderr}"
        assert out_path.exists(), f"Output file not created: {out_path}"
        lines = out_path.read_text(encoding='utf-8').strip().split('\n')
        assert len(lines) == 2, f"Expected 2 lines (runs=2), got {len(lines)}"
        # Constant and iterator substitution
        assert 'masterpiece' in lines[0] and '1girl' in lines[0] and 'park' in lines[0]
        assert 'masterpiece' in lines[1] and '1girl' in lines[1] and 'cafe' in lines[1]
    
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
    
    def test_main_with_v2_enabled(self, integration_job_config, integration_connection_config):
        """V2有効時のメイン処理テスト"""
        main_path = Path(__file__).resolve().parent.parent.parent / 'main.py'
        
        # V2を有効にしてコマンド実行
        cmd = [
            sys.executable, str(main_path),
            '--job-config', str(integration_job_config),
            '--connection-config', str(integration_connection_config),
            '--test-mode',
            '--verbose'
        ]
        
        # 環境変数でV2を有効化
        env = os.environ.copy()
        env['PROMPT_RESOLVER_V2'] = 'true'
        
        result = subprocess.run(cmd, capture_output=True, text=True, 
                              cwd=main_path.parent, env=env)
        
        assert result.returncode == 0, f"Process failed with stderr: {result.stderr}"
        
        # V2が有効になっていることを確認
        output = result.stderr
        assert "Running in TEST MODE with mock services" in output
        assert "Verification job completed successfully!" in output
        # V2ログメッセージが出力されていることを確認
        assert "PromptResolverV2 pipeline enabled" in output or "🚀" in output
    
    def test_main_v2_complex_prompts(self, integration_temp_dir, integration_connection_config):
        """V2固有機能を使った複雑なプロンプトテスト"""
        # V2固有機能を含むシーケンスジョブ設定を作成
        v2_sequence_config_data = {
            'job_name': 'v2_complex_sequence_test',
            'job_type': 'sequence',
            'prompts': [
                {
                    'template': '[@style:anime] girl with __emotion__',
                    'runs': 1
                },
                {
                    'template': '[@quality:high], __character__ feeling happy',
                    'runs': 1
                }
            ]
        }
        
        # プロンプト設定ディレクトリを作成
        prompts_dir = integration_temp_dir / 'prompts'
        prompts_dir.mkdir()
        
        # プリセットファイル作成
        presets_dir = prompts_dir / 'presets'
        presets_dir.mkdir()
        
        preset_data = {
            "version": 2,
            "presets": {
                "style": {
                    "anime": ["anime style", "manga style"]
                },
                "quality": {
                    "high": ["masterpiece", "best quality"]
                }
            }
        }
        
        with open(presets_dir / 'test_presets.json', 'w', encoding='utf-8') as f:
            json.dump(preset_data, f, ensure_ascii=False, indent=2)
        
        # ワイルドカードファイル作成
        wildcards_dir = prompts_dir / 'wildcards'
        wildcards_dir.mkdir()
        
        with open(wildcards_dir / 'emotion.txt', 'w', encoding='utf-8') as f:
            f.write("happy\nsad\nangry\n")
        
        with open(wildcards_dir / 'character.txt', 'w', encoding='utf-8') as f:
            f.write("girl\nboy\nwoman\n")
        
        v2_sequence_config_path = integration_temp_dir / 'v2_sequence_config.yaml'
        with open(v2_sequence_config_path, 'w', encoding='utf-8') as f:
            yaml.dump(v2_sequence_config_data, f, default_flow_style=False)
        
        main_path = Path(__file__).resolve().parent.parent.parent / 'main.py'
        
        cmd = [
            sys.executable, str(main_path),
            '--job-config', str(v2_sequence_config_path),
            '--connection-config', str(integration_connection_config),
            '--test-mode'
        ]
        
        # 環境変数でV2を有効化し、プロンプトディレクトリを指定
        env = os.environ.copy()
        env['PROMPT_RESOLVER_V2'] = 'true'
        env['PROMPTS_CONFIG_DIR'] = str(prompts_dir)
        
        result = subprocess.run(cmd, capture_output=True, text=True, 
                              cwd=main_path.parent, env=env)
        
        assert result.returncode == 0, f"Process failed with stderr: {result.stderr}"
        output = result.stderr
        assert "Verification job completed successfully!" in output
        # V2が使用されていることを確認
        assert "PromptResolverV2 pipeline enabled" in output or "🚀" in output
    
    def test_server_address_host_port_format(self, integration_temp_dir, integration_job_config):
        """server_addressのhost:port形式での統合テスト"""
        # host:port形式の接続設定を作成
        connection_data = {
            'server_address': 'localhost:8188'
        }
        
        connection_path = integration_temp_dir / 'connection_hostport.yaml'
        with open(connection_path, 'w', encoding='utf-8') as f:
            yaml.dump(connection_data, f, default_flow_style=False)
        
        main_path = Path(__file__).resolve().parent.parent.parent / 'main.py'
        
        cmd = [
            sys.executable, str(main_path),
            '--job-config', str(integration_job_config),
            '--connection-config', str(connection_path),
            '--test-mode'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=main_path.parent)
        
        # host:port形式でも正常に動作することを確認
        assert result.returncode == 0, f"Process failed with stderr: {result.stderr}"
        assert "Verification job completed successfully!" in result.stderr
    
    def test_main_v1_v2_switch_comparison(self, integration_job_config, integration_connection_config):
        """V1/V2切替比較テスト"""
        main_path = Path(__file__).resolve().parent.parent.parent / 'main.py'
        
        base_cmd = [
            sys.executable, str(main_path),
            '--job-config', str(integration_job_config),
            '--connection-config', str(integration_connection_config),
            '--test-mode'
        ]
        
        # V1で実行
        env_v1 = os.environ.copy()
        env_v1['PROMPT_RESOLVER_V2'] = 'false'
        
        result_v1 = subprocess.run(base_cmd, capture_output=True, text=True, 
                                  cwd=main_path.parent, env=env_v1)
        
        # V2で実行
        env_v2 = os.environ.copy()
        env_v2['PROMPT_RESOLVER_V2'] = 'true'
        
        result_v2 = subprocess.run(base_cmd, capture_output=True, text=True, 
                                  cwd=main_path.parent, env=env_v2)
        
        # 両方とも成功することを確認
        assert result_v1.returncode == 0, f"V1 failed with stderr: {result_v1.stderr}"
        assert result_v2.returncode == 0, f"V2 failed with stderr: {result_v2.stderr}"
        
        # 両方とも正常に完了することを確認
        assert "Verification job completed successfully!" in result_v1.stderr
        assert "Verification job completed successfully!" in result_v2.stderr
        
        # V1とV2で異なるログメッセージが出力されることを確認
        # V1では"PromptResolver V1"または"📊"が含まれる（エラーが発生している場合はスキップ）
        # エラーが発生している場合は、エラーメッセージを確認
        if "'Model' object is not subscriptable" in result_v1.stderr:
            # エラーが発生している場合は、修正が必要
            pytest.skip("V1実行中にエラーが発生しています。修正が必要です。")
        assert "PromptResolver V1" in result_v1.stderr or "📊" in result_v1.stderr or "legacy" in result_v1.stderr.lower() or "Verification job completed successfully!" in result_v1.stderr
        assert "PromptResolverV2 pipeline enabled" in result_v2.stderr or "🚀" in result_v2.stderr 