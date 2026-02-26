# comfyui (ComfyV)

ComfyUI API を使った自動画像生成・検証フレームワーク。

## 共通ルール

Git 運用・コミット規約・PR手順・worktree操作は **`../.agents/AGENTS.md`** を参照。

## このリポ固有のルール

### 開発環境

- Python 3.12+、パッケージ管理は `uv`
- セットアップ: `uv venv && uv sync`
- テスト: `uv run pytest`

### コード規約

- 型ヒント必須（`mypy` 相当の厳格さ）
- テストなしの PR は原則不可（既存テストが通ることを確認）
- 新機能には対応するテストを追加する

### 主要ドキュメント

- 設計・仕様: `documents/design_and_specification.md`
- 設定・プロンプト記法: `documents/config_and_prompt_guide.md`
- 実装計画・タスクメモ: `documents/plans/`（comfyui は `docs/` ではなく `documents/` を使用）

### プロジェクト構成

```
core/            - コアモジュール（config, api_client, executors, resolver...）
core/resolver/   - PromptResolver V2 パイプライン（6ステージ）
core/executors/  - 実行エンジン（GridSearch / Sequence）
core/schemas/    - Pydantic モデル
configs/         - ジョブ設定・ワークフロー・プロンプト（Git管理外）
tests/           - pytest テストスイート
documents/       - 設計ドキュメント
```

### 注意事項

- `configs/` は `.gitignore` により Git 管理外（ジョブ設定・画像等を含むため）
- PromptResolver V1 (`core/prompt_resolver.py`) はレガシー。新規実装は V2 を使う
