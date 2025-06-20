import argparse
import sys
import logging
from pathlib import Path

from core.config import Config
from core.executors.base_executor import BaseExecutor
from core.executors.sequence_executor import SequenceJobExecutor
from core.executors.grid_search_executor import GridSearchJobExecutor

# プロジェクトルートをPythonパスに追加
sys.path.append(str(Path(__file__).resolve().parent))


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
        required=True, 
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
    args = parser.parse_args()

    # ロガーをセットアップ
    setup_logging(args.verbose)


    try:
        logging.info("Initializing ComfyV...")
        config = Config(
            job_config_path=args.job_config, 
            connection_config_path=args.connection_config
        )
        job_type = config.job_data.get('job_type', 'grid_search') # デフォルトはgrid_search

        if job_type == 'grid_search':
            executor = GridSearchJobExecutor(config)
        elif job_type == 'sequence':
            executor = SequenceJobExecutor(config)
        else:
            raise ValueError(f"Unknown job_type: {job_type}")

        executor.run()
        logging.info("\n🎉 Verification job completed successfully!")

    except FileNotFoundError as e:
        logging.error(f"❌ File not found: {e}")
    except (ValueError, TypeError, KeyError) as e:
        logging.error(f"❌ Configuration Error: {e}")
    except Exception as e:
        logging.critical(f"❌ An unexpected error occurred: {e}", exc_info=True)

if __name__ == "__main__":
    main()