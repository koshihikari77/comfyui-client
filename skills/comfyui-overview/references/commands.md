# よく使うコマンド

## 前提

- 実行ディレクトリ: 任意
- 必要な前提: `uv`, ComfyUI server 接続設定

## 基本

```bash
uv run --project /mnt/c/Users/inada/obsidian/base/03_projects/comfyui comfyv --help
```

- 用途: CLI 全体を確認する

```bash
uv run --project /mnt/c/Users/inada/obsidian/base/03_projects/comfyui comfyv run /mnt/c/Users/inada/obsidian/base/03_projects/comfyui/configs/jobs/example.yaml --test-mode --verbose
```

- 用途: server なしで job 実行フローを確認する

```bash
uv run --project /mnt/c/Users/inada/obsidian/base/03_projects/comfyui pytest
```

- 用途: テストを実行する
