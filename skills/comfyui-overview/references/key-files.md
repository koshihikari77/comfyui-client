# 重要ファイル

## 最優先

- `/mnt/c/Users/inada/obsidian/base/03_projects/comfyui/AGENTS.md` - repo 固有の開発ルールと主要ドキュメント
- `/mnt/c/Users/inada/obsidian/base/03_projects/comfyui/README.md` - ComfyV の全体像
- `/mnt/c/Users/inada/obsidian/base/03_projects/comfyui/pyproject.toml` - `comfyv` entrypoint と依存関係
- `/mnt/c/Users/inada/obsidian/base/03_projects/comfyui/core/cli.py` - CLI 入口
- `/mnt/c/Users/inada/obsidian/base/03_projects/comfyui/core/config.py` - job / scene_delta 読み込み
- `/mnt/c/Users/inada/obsidian/base/03_projects/comfyui/core/prompt_resolver_v2.py` - 現行の prompt 解決系

## 状況別

### 実行フローを知りたい

- `/mnt/c/Users/inada/obsidian/base/03_projects/comfyui/core/executors/grid_search_executor.py`
- `/mnt/c/Users/inada/obsidian/base/03_projects/comfyui/core/executors/sequence_executor.py`
- `/mnt/c/Users/inada/obsidian/base/03_projects/comfyui/core/service_container.py`

### workflow / node 解決を知りたい

- `/mnt/c/Users/inada/obsidian/base/03_projects/comfyui/core/workflow_loader.py`
- `/mnt/c/Users/inada/obsidian/base/03_projects/comfyui/configs/workflows/`

### 結果保存を知りたい

- `/mnt/c/Users/inada/obsidian/base/03_projects/comfyui/core/database.py`
- `/mnt/c/Users/inada/obsidian/base/03_projects/comfyui/results/`
