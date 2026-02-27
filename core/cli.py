from __future__ import annotations

import json
import logging
import os
import re
import sys
from importlib import metadata
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer

from .config import Config
from .executors.grid_search_executor import GridSearchJobExecutor
from .executors.sequence_executor import SequenceJobExecutor
from .mock_services import MockServiceContainer
from .prompt_resolver_v2 import PromptResolverV2
from .scene_selection import (
    extract_scene_delta_id_index_map,
    filter_config_prompts_inplace,
    parse_scene_selection,
)
from .service_container import ServiceContainer

app = typer.Typer(
    help="ComfyV 画像生成検証CLI",
    no_args_is_help=True,
    add_completion=False,
)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONNECTION_CONFIG = PROJECT_ROOT / "configs/connection_config.yaml"
DEFAULT_PROMPTS_DIR = PROJECT_ROOT / "configs/prompts"
ENV_CONNECTION_CONFIG = "COMFYV_CONNECTION_CONFIG"
ENV_PROMPTS_DIR = "PROMPTS_CONFIG_DIR"


def _get_version() -> str:
    try:
        return metadata.version("comfyv")
    except Exception:
        return "unknown"


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"comfyv {_get_version()}")
        raise typer.Exit(code=0)


@app.callback()
def callback(
    version: bool = typer.Option(  # noqa: B008
        False,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="バージョンを表示して終了",
    ),
) -> None:
    """ComfyV CLI."""
    _ = version


def _setup_logging(verbose: bool, quiet: bool) -> None:
    log_level = logging.ERROR if quiet else (logging.DEBUG if verbose else logging.INFO)
    if quiet:
        os.environ["COMFYV_QUIET"] = "1"
    else:
        os.environ.pop("COMFYV_QUIET", None)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - [%(name)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stderr,
        force=True,
    )


def _json_dump(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False)


def _handle_error(exc: Exception, *, json_output: bool, verbose: bool) -> None:
    if verbose:
        logger.exception("コマンド実行に失敗しました")
    else:
        logger.error(str(exc))

    if json_output:
        typer.echo(
            _json_dump(
                {
                    "status": "error",
                    "error": type(exc).__name__,
                    "message": str(exc),
                }
            )
        )
    else:
        typer.echo(f"Error: {exc}", err=True)
    raise typer.Exit(code=1)


def _resolve_job_config_path(job_config: Path) -> Path:
    return job_config.expanduser().resolve()


def _resolve_connection_config_path(config: Optional[Path]) -> Path:
    if config is not None:
        return config.expanduser().resolve()

    env_path = os.getenv(ENV_CONNECTION_CONFIG)
    if env_path:
        return Path(env_path).expanduser().resolve()

    return DEFAULT_CONNECTION_CONFIG.resolve()


def _resolve_prompts_dir() -> Path:
    env_path = os.getenv(ENV_PROMPTS_DIR)
    if env_path:
        return Path(env_path).expanduser().resolve()
    return DEFAULT_PROMPTS_DIR.resolve()


def _preprocess_iterators_for_dump(config: Config, resolver: PromptResolverV2) -> Dict[str, List[str]]:
    resolved: Dict[str, List[str]] = {}
    iterators = getattr(config, "iterators", None) or {}
    if not iterators:
        return resolved

    for iterator_name, iterator_value in iterators.items():
        try:
            if isinstance(iterator_value, list):
                resolved[iterator_name] = list(iterator_value)
            elif isinstance(iterator_value, dict) and "expand_preset" in iterator_value:
                preset_key = iterator_value["expand_preset"]
                group_names = resolver.get_preset_groups(preset_key)
                resolved[iterator_name] = [f"<preset:{preset_key}#{group}>" for group in group_names]
            else:
                resolved[iterator_name] = []
        except Exception as exc:
            logger.warning("Failed to preprocess iterator %s: %s", iterator_name, exc)
            resolved[iterator_name] = []
    return resolved


def _substitute_constants(template: str, constants: Dict[str, Any]) -> str:
    if not constants:
        return template

    pattern = r"%([a-zA-Z_][a-zA-Z0-9_]*)%"

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in constants:
            return match.group(0)
        value = constants[name]
        return ", ".join(value) if isinstance(value, list) else str(value)

    return re.sub(pattern, replace, template)


def _substitute_iterators(
    template: str,
    resolved_iterators: Dict[str, List[str]],
    counters: Dict[str, int],
) -> str:
    if not resolved_iterators:
        return template

    pattern = r"\$\[([a-zA-Z_][a-zA-Z0-9_]*)\]"

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in resolved_iterators or not resolved_iterators[name]:
            return match.group(0)
        values = resolved_iterators[name]
        index = counters.get(name, 0) % len(values)
        counters[name] = counters.get(name, 0) + 1
        return values[index]

    return re.sub(pattern, replace, template)


def _build_v2_config(config: Config) -> Dict[str, Any]:
    return {
        "ignore_tags": config.ignore_tags,
        "ignore_groups": config.ignore_groups,
        "placeholders": config.placeholders,
        "locale": config.locale,
        "strict_level": config.strict_level,
        "seed": config.seed,
    }


def _create_resolver(config: Config) -> PromptResolverV2:
    prompts_dir = _resolve_prompts_dir()
    return PromptResolverV2(str(prompts_dir), _build_v2_config(config))


def _generate_resolved_prompts(config: Config, resolver: PromptResolverV2) -> List[str]:
    lines: List[str] = []
    constants = getattr(config, "constants", None) or {}
    default_runs = getattr(config, "default_runs", 1) or 1
    resolved_iterators = _preprocess_iterators_for_dump(config, resolver)
    iterator_counters = {name: 0 for name in resolved_iterators}

    for prompt_def in config.prompts:
        template = prompt_def.template
        num_runs = getattr(prompt_def, "runs", None) or default_runs
        for index in range(num_runs):
            processed = _substitute_constants(template, constants)
            processed = _substitute_iterators(processed, resolved_iterators, iterator_counters)
            resolved = resolver.resolve_nth(processed, index, cycle=True)
            lines.append(resolved)
    return lines


def _apply_scene_filter(config: Config, scenes: str) -> None:
    ids_by_index, index_by_id = extract_scene_delta_id_index_map(config.job_data)
    selected_indices = parse_scene_selection(
        scenes,
        index_by_id=index_by_id,
        max_index=len(ids_by_index),
    )
    if not selected_indices:
        raise ValueError("scene selection is empty")
    filter_config_prompts_inplace(config, selected_indices)


@app.command()
def run(
    job_config: Path = typer.Argument(  # noqa: B008
        ...,
        help="ジョブ設定YAMLのパス",
    ),
    config: Optional[Path] = typer.Option(  # noqa: B008
        None,
        "--config",
        "-c",
        help=(
            "接続設定YAMLのパス。"
            "未指定時は --config > COMFYV_CONNECTION_CONFIG > configs/connection_config.yaml の順で解決"
        ),
    ),
    scenes: Optional[str] = typer.Option(  # noqa: B008
        None,
        "--scenes",
        help='scene_delta の選択指定（例: "0,2,base,5-12"）',
    ),
    test_mode: bool = typer.Option(False, "--test-mode", help="モックサービスで実行"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="詳細ログを表示"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="進捗ログを抑制"),
    json_output: bool = typer.Option(False, "--json", help="結果をJSONで出力"),
) -> None:
    """ComfyVジョブを実行する。"""
    _setup_logging(verbose, quiet)

    try:
        job_config_path = _resolve_job_config_path(job_config)
        connection_config_path = _resolve_connection_config_path(config)

        cfg = Config(
            job_config_path=str(job_config_path),
            connection_config_path=str(connection_config_path),
        )

        if test_mode:
            logger.info("テストモードで実行します（モックサービス使用）")
            service_container = MockServiceContainer()
        else:
            service_container = ServiceContainer(cfg)

        job_type = cfg.job_data.get("job_type", "grid_search")
        if job_type == "grid_search":
            if scenes:
                raise ValueError("--scenes は sequence ジョブでのみ指定できます")
            executor = GridSearchJobExecutor(cfg, service_container)
        elif job_type == "sequence":
            if scenes:
                _apply_scene_filter(cfg, scenes)
            executor = SequenceJobExecutor(cfg, service_container)
        else:
            raise ValueError(f"Unknown job_type: {job_type}")

        executor.run()
        logger.info("ジョブ実行が正常に完了しました")
        result = {
            "status": "ok",
            "job_name": cfg.job_name,
            "job_type": job_type,
            "test_mode": test_mode,
        }
        if json_output:
            typer.echo(_json_dump(result))
    except Exception as exc:
        _handle_error(exc, json_output=json_output, verbose=verbose)


@app.command("eval-prompt")
def eval_prompt(
    template: str = typer.Argument(..., help="評価するテンプレート文字列"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="詳細ログを表示"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="進捗ログを抑制"),
    json_output: bool = typer.Option(False, "--json", help="結果をJSONで出力"),
) -> None:
    """PromptResolverV2で1件のプロンプトを評価する。"""
    _setup_logging(verbose, quiet)

    try:
        resolver = PromptResolverV2(str(_resolve_prompts_dir()))
        resolved = resolver.resolve(template)
        if json_output:
            typer.echo(
                _json_dump(
                    {
                        "status": "ok",
                        "template": template,
                        "resolved": resolved,
                    }
                )
            )
        else:
            typer.echo(resolved)
    except Exception as exc:
        _handle_error(exc, json_output=json_output, verbose=verbose)


@app.command("dump-prompts")
def dump_prompts(
    job_config: Path = typer.Argument(  # noqa: B008
        ...,
        help="sequenceジョブ設定YAMLのパス",
    ),
    output: Path = typer.Option(  # noqa: B008
        ...,
        "--output",
        "-o",
        help="解決済みプロンプトの出力先ファイル",
    ),
    config: Optional[Path] = typer.Option(  # noqa: B008
        None,
        "--config",
        "-c",
        help=(
            "接続設定YAMLのパス。"
            "未指定時は --config > COMFYV_CONNECTION_CONFIG > configs/connection_config.yaml の順で解決"
        ),
    ),
    scenes: Optional[str] = typer.Option(
        None,
        "--scenes",
        help='scene_delta の選択指定（例: "0,2,base,5-12"）',
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="詳細ログを表示"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="進捗ログを抑制"),
    json_output: bool = typer.Option(False, "--json", help="結果をJSONで出力"),
) -> None:
    """全プロンプトを解決し、1行1件でファイル出力する。"""
    _setup_logging(verbose, quiet)

    try:
        job_config_path = _resolve_job_config_path(job_config)
        connection_config_path = _resolve_connection_config_path(config)
        output_path = output.expanduser().resolve()

        cfg = Config(
            job_config_path=str(job_config_path),
            connection_config_path=str(connection_config_path),
        )
        job_type = cfg.job_data.get("job_type", "grid_search")
        if job_type != "sequence":
            raise ValueError("dump-prompts は sequence ジョブ専用です")

        if scenes:
            _apply_scene_filter(cfg, scenes)

        resolver = _create_resolver(cfg)
        lines = _generate_resolved_prompts(cfg, resolver)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(lines), encoding="utf-8")

        if json_output:
            typer.echo(
                _json_dump(
                    {
                        "status": "ok",
                        "output": str(output_path),
                        "count": len(lines),
                    }
                )
            )
        else:
            typer.echo(str(output_path))
    except Exception as exc:
        _handle_error(exc, json_output=json_output, verbose=verbose)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
