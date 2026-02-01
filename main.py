import argparse
import re
import sys
import logging
from pathlib import Path
from typing import Dict, List

from core.config import Config
from core.service_container import ServiceContainer
from core.mock_services import MockServiceContainer
from core.executors.base_executor import BaseExecutor
from core.executors.sequence_executor import SequenceJobExecutor
from core.executors.grid_search_executor import GridSearchJobExecutor
from core.prompt_resolver_v2 import PromptResolverV2
from core.scene_selection import (
    extract_scene_delta_id_index_map,
    filter_config_prompts_inplace,
    parse_scene_selection,
)

# プロジェクトルートをPythonパスに追加
sys.path.append(str(Path(__file__).resolve().parent))

logger = logging.getLogger(__name__)


def _preprocess_iterators_for_dump(config: Config, resolver: PromptResolverV2) -> Dict[str, List[str]]:
    """Iteratorの事前処理（expand_preset解決）。SequenceExecutor._preprocess_iterators と同等。"""
    resolved = {}
    iterators = getattr(config, 'iterators', None) or {}
    if not iterators:
        return resolved
    for iterator_name, iterator_value in iterators.items():
        try:
            if isinstance(iterator_value, list):
                resolved[iterator_name] = list(iterator_value)
            elif isinstance(iterator_value, dict) and 'expand_preset' in iterator_value:
                preset_key = iterator_value['expand_preset']
                group_names = resolver.get_preset_groups(preset_key)
                resolved[iterator_name] = [f"<preset:{preset_key}#{g}>" for g in group_names]
            else:
                resolved[iterator_name] = []
        except Exception as e:
            logger.warning("Failed to preprocess iterator %s: %s", iterator_name, e)
            resolved[iterator_name] = []
    return resolved


def _substitute_constants(template: str, constants: dict) -> str:
    """%constant_name% を置換。SequenceExecutor._substitute_constant_syntax と同等。値がlistの場合は ', '.join する。"""
    if not constants:
        return template
    pattern = r'%([a-zA-Z_][a-zA-Z0-9_]*)%'
    def replace(m):
        name = m.group(1)
        val = constants.get(name, m.group(0))
        if val is m.group(0):  # not found
            return val
        return ", ".join(val) if isinstance(val, list) else val
    return re.sub(pattern, replace, template)


def _substitute_iterators(template: str, resolved_iterators: Dict[str, List[str]], counters: Dict[str, int]) -> str:
    """$[name] を置換（counters を更新）。SequenceExecutor._substitute_iterator_syntax と同等。"""
    if not resolved_iterators:
        return template
    pattern = r'\$\[([a-zA-Z_][a-zA-Z0-9_]*)\]'
    def replace(m):
        name = m.group(1)
        if name not in resolved_iterators or not resolved_iterators[name]:
            return m.group(0)
        lst = resolved_iterators[name]
        idx = counters.get(name, 0) % len(lst)
        counters[name] = counters.get(name, 0) + 1
        return lst[idx]
    return re.sub(pattern, replace, template)


def generate_resolved_prompts(config: Config, resolver: PromptResolverV2) -> List[str]:
    """
    Config と PromptResolverV2 から、全 run 分の解決済みプロンプトを生成する（副作用なしで実行順序と同一）。
    """
    lines = []
    constants = getattr(config, 'constants', None) or {}
    default_runs = getattr(config, 'default_runs', 1) or 1
    resolved_iterators = _preprocess_iterators_for_dump(config, resolver)
    iterator_counters = {name: 0 for name in resolved_iterators}

    for prompt_def in config.prompts:
        template = prompt_def.template
        num_runs = getattr(prompt_def, 'runs', None) or default_runs
        for _ in range(num_runs):
            processed = _substitute_constants(template, constants)
            processed = _substitute_iterators(processed, resolved_iterators, iterator_counters)
            resolved = resolver.resolve(processed)
            lines.append(resolved)
    return lines


def setup_logging(verbose: bool):
    """ロギングの基本設定を行う"""
    log_level = logging.DEBUG if verbose else logging.INFO
    log_format = '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def main():
    parser = argparse.ArgumentParser(description="ComfyV Verification Framework")
    parser.add_argument(
        "-j", "--job-config", 
        help="Path to the job config YAML file (e.g., configs/lora_verify_config.yml)"
    )
    parser.add_argument(
        "-c", "--connection-config", 
        default="configs/connection_config.yaml",
        help="Path to the connection config YAML file (default: configs/connection_config.yml)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging (DEBUG level)."
    )
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Run in test mode with mock services (for development/testing)."
    )
    parser.add_argument(
        "--eval-prompt",
        help="Evaluate a single prompt and display the result"
    )
    parser.add_argument(
        "--dump-prompts",
        metavar="PATH",
        help="Load job config, resolve all prompts (constants/iterators/preset/wildcard), write one per line to PATH and exit (sequence jobs only)"
    )
    parser.add_argument(
        "--scenes",
        metavar="SPEC",
        help="scene_delta の ID / index / 範囲（a-b）をカンマ区切りで指定して部分実行する。例: \"0,2,base_sitting,5-12\""
    )
    args = parser.parse_args()

    # ロガーをセットアップ
    setup_logging(args.verbose)

    # dump-promptsモードの処理
    if args.dump_prompts:
        if not args.job_config:
            logging.error("❌ --job-config is required when using --dump-prompts")
            sys.exit(1)
        try:
            config = Config(
                job_config_path=args.job_config,
                connection_config_path=args.connection_config,
            )
            job_type = config.job_data.get("job_type", "grid_search")
            if job_type != "sequence":
                logging.error("❌ --dump-prompts supports only sequence jobs (job_type: sequence)")
                sys.exit(1)
            if args.scenes:
                ids_by_index, index_by_id = extract_scene_delta_id_index_map(config.job_data)
                selected_indices = parse_scene_selection(
                    args.scenes, index_by_id=index_by_id, max_index=len(ids_by_index)
                )
                if not selected_indices:
                    raise ValueError("--scenes の指定が空です")
                filter_config_prompts_inplace(config, selected_indices)

            v2_config = {
                "ignore_tags": config.ignore_tags,
                "ignore_groups": config.ignore_groups,
                "placeholders": config.placeholders,
                "locale": config.locale,
                "strict_level": config.strict_level,
                "seed": config.seed,
            }
            resolver = PromptResolverV2("configs/prompts", v2_config)
            lines = generate_resolved_prompts(config, resolver)
            out_path = Path(args.dump_prompts)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text("\n".join(lines), encoding="utf-8")
            logging.info("Dumped %d resolved prompt(s) to %s", len(lines), out_path)
            return
        except Exception as e:
            logging.error("❌ Dump prompts failed: %s", e, exc_info=True)
            sys.exit(1)

    # eval-promptモードの処理
    if args.eval_prompt:
        try:
            # プロンプト評価モード
            print(f"Original: {args.eval_prompt}")
            
            # PromptResolverV2で評価
            resolver = PromptResolverV2("configs/prompts")
            resolved = resolver.resolve(args.eval_prompt)
            
            print(f"Resolved: {resolved}")
            return
            
        except Exception as e:
            logging.error(f"❌ Prompt evaluation failed: {e}")
            sys.exit(1)

    # job-configが必要なモード
    if not args.job_config:
        logging.error("❌ --job-config is required when not using --eval-prompt")
        sys.exit(1)

    try:
        logging.info("Initializing ComfyV...")
        config = Config(
            job_config_path=args.job_config, 
            connection_config_path=args.connection_config
        )
        
        # DIコンテナを初期化（テストモードかどうかで切り替え）
        if args.test_mode:
            logging.info("🧪 Running in TEST MODE with mock services")
            service_container = MockServiceContainer()
        else:
            service_container = ServiceContainer(config)
        
        job_type = config.job_data.get('job_type', 'grid_search') # デフォルトはgrid_search

        if job_type == 'grid_search':
            if args.scenes:
                raise ValueError("--scenes は scene_delta を使う sequence ジョブ専用です")
            executor = GridSearchJobExecutor(config, service_container)
        elif job_type == 'sequence':
            if args.scenes:
                ids_by_index, index_by_id = extract_scene_delta_id_index_map(config.job_data)
                selected_indices = parse_scene_selection(
                    args.scenes, index_by_id=index_by_id, max_index=len(ids_by_index)
                )
                if not selected_indices:
                    raise ValueError("--scenes の指定が空です")
                filter_config_prompts_inplace(config, selected_indices)
            executor = SequenceJobExecutor(config, service_container)
        else:
            raise ValueError(f"Unknown job_type: {job_type}")

        executor.run()
        logging.info("\n🎉 Verification job completed successfully!")

    except FileNotFoundError as e:
        logging.error(f"❌ File not found: {e}")
        sys.exit(1)
    except (ValueError, TypeError, KeyError) as e:
        logging.error(f"❌ Configuration Error: {e}")
        sys.exit(1)
    except Exception as e:
        logging.critical(f"❌ An unexpected error occurred: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()