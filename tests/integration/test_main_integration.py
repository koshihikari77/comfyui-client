"""
ComfyV CLI 統合テスト
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def integration_temp_dir() -> Path:
    temp_dir = Path(tempfile.mkdtemp())
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir)


@pytest.fixture
def integration_connection_config(integration_temp_dir: Path) -> Path:
    config_data = {"server_address": "http://localhost:8188"}
    config_path = integration_temp_dir / "connection_config.yaml"
    config_path.write_text(yaml.dump(config_data, default_flow_style=False), encoding="utf-8")
    return config_path


@pytest.fixture
def integration_job_config(integration_temp_dir: Path) -> Path:
    config_data = {
        "job_name": "integration_test_job",
        "job_type": "grid_search",
        "base_workflow": "test_workflow.json",
        "variables": [
            {
                "node_id": 1,
                "input_name": "test_param",
                "values": ["value1", "value2"],
            }
        ],
    }

    config_path = integration_temp_dir / "job_config.yaml"
    config_path.write_text(yaml.dump(config_data, default_flow_style=False), encoding="utf-8")

    workflow_data = {
        "1": {
            "inputs": {"test_param": "default_value"},
            "class_type": "TestNode",
        }
    }
    workflow_path = integration_temp_dir / "test_workflow.json"
    workflow_path.write_text(json.dumps(workflow_data), encoding="utf-8")
    return config_path


def run_cli(args: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    project_root = Path(__file__).resolve().parents[2]
    cmd = [sys.executable, "-m", "core.cli", *args]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=project_root,
        env=env,
    )


class TestCLIIntegration:
    def test_run_grid_search_test_mode(
        self,
        integration_job_config: Path,
        integration_connection_config: Path,
    ) -> None:
        result = run_cli(
            [
                "run",
                str(integration_job_config),
                "--config",
                str(integration_connection_config),
                "--test-mode",
                "--verbose",
            ]
        )
        assert result.returncode == 0, result.stderr
        assert "テストモードで実行します" in result.stderr
        assert "ジョブ実行が正常に完了しました" in result.stderr

    def test_run_sequence_test_mode(
        self,
        integration_temp_dir: Path,
        integration_connection_config: Path,
    ) -> None:
        sequence_config_data = {
            "job_name": "integration_sequence_test",
            "job_type": "sequence",
            "prompts": [
                {"template": "test prompt 1", "runs": 1},
                {"template": "test prompt 2", "runs": 1},
            ],
        }
        sequence_config_path = integration_temp_dir / "sequence_config.yaml"
        sequence_config_path.write_text(
            yaml.dump(sequence_config_data, default_flow_style=False), encoding="utf-8"
        )

        result = run_cli(
            [
                "run",
                str(sequence_config_path),
                "--config",
                str(integration_connection_config),
                "--test-mode",
            ]
        )
        assert result.returncode == 0, result.stderr
        assert "ジョブ実行が正常に完了しました" in result.stderr

    def test_dump_prompts(
        self,
        integration_temp_dir: Path,
        integration_connection_config: Path,
    ) -> None:
        dump_job_data = {
            "job_name": "dump_prompts_test",
            "job_type": "sequence",
            "constants": {"base": "masterpiece, best quality"},
            "iterators": {"loc": ["park", "cafe"]},
            "prompts": [{"template": "%base%, 1girl, $[loc]", "runs": 2}],
        }
        job_path = integration_temp_dir / "dump_prompts_job.yaml"
        job_path.write_text(yaml.dump(dump_job_data, default_flow_style=False), encoding="utf-8")
        out_path = integration_temp_dir / "out_prompts.txt"

        result = run_cli(
            [
                "dump-prompts",
                str(job_path),
                "--config",
                str(integration_connection_config),
                "--output",
                str(out_path),
            ]
        )
        assert result.returncode == 0, result.stderr
        assert out_path.exists()
        lines = out_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2
        assert "masterpiece" in lines[0] and "park" in lines[0]
        assert "masterpiece" in lines[1] and "cafe" in lines[1]

    def test_eval_prompt(self) -> None:
        result = run_cli(["eval-prompt", "1girl, smiling"])
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() != ""

    def test_json_error_output(
        self,
        integration_connection_config: Path,
    ) -> None:
        result = run_cli(
            [
                "run",
                "nonexistent_job.yaml",
                "--config",
                str(integration_connection_config),
                "--test-mode",
                "--json",
            ]
        )
        assert result.returncode == 1
        payload = json.loads(result.stdout)
        assert payload["status"] == "error"
        assert payload["error"] == "FileNotFoundError"

    def test_unknown_legacy_option_rejected(self) -> None:
        result = run_cli(["run", "--job-config", "foo.yaml"])
        assert result.returncode == 2
        assert "--job-config" in result.stderr

    def test_help_outputs_expected_options(self) -> None:
        root_help = run_cli(["--help"])
        assert root_help.returncode == 0
        assert "run" in root_help.stdout
        assert "dump-prompts" in root_help.stdout
        assert "eval-prompt" in root_help.stdout

        run_help = run_cli(["run", "--help"])
        assert run_help.returncode == 0
        assert "--config" in run_help.stdout
        assert "--json" in run_help.stdout
        assert "--quiet" in run_help.stdout
        assert "--connection-config" not in run_help.stdout

    def test_config_priority_explicit_over_env(
        self,
        integration_job_config: Path,
        integration_connection_config: Path,
    ) -> None:
        env = os.environ.copy()
        env["COMFYV_CONNECTION_CONFIG"] = "/tmp/does-not-exist.yaml"

        result = run_cli(
            [
                "run",
                str(integration_job_config),
                "--config",
                str(integration_connection_config),
                "--test-mode",
            ],
            env=env,
        )
        assert result.returncode == 0, result.stderr

    def test_config_priority_env_over_default(
        self,
        integration_job_config: Path,
    ) -> None:
        env = os.environ.copy()
        env["COMFYV_CONNECTION_CONFIG"] = "/tmp/does-not-exist.yaml"

        result = run_cli(
            [
                "run",
                str(integration_job_config),
                "--test-mode",
                "--json",
            ],
            env=env,
        )
        assert result.returncode == 1
        payload = json.loads(result.stdout)
        assert payload["status"] == "error"
        assert payload["error"] == "FileNotFoundError"
