import argparse
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
sys.path.append(str(Path(__file__).resolve().parent))

from core.config import Config
from core.executor import JobExecutor

def main():
    parser = argparse.ArgumentParser(description="ComfyV Verification Framework")
    parser.add_argument(
        "-c", "--config", 
        required=True, 
        help="Path to the config YAML file (e.g., configs/lora_verify_config.yaml)"
    )
    args = parser.parse_args()

    try:
        config = Config(args.config)
        executor = JobExecutor(config)
        executor.run()
        print("\n🎉 Verification job completed successfully!")

    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
    except (ValueError, TypeError, KeyError) as e:
        print(f"❌ Configuration Error: {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()