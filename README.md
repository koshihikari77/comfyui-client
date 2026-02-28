# ComfyV - ComfyUI Verification Framework

ComfyVは、ComfyUI APIを利用した**拡張性の高い自動画像生成・検証フレームワーク**です。

## 🎯 主な機能

- **グリッドサーチ**: 複数パラメータの全組み合わせを自動検証
- **シーケンス実行**: 定義されたプロンプトリストを順次実行
- **プロンプト解決**: プリセット、ワイルドカード、プレースホルダーによる柔軟なプロンプト生成
- **ワークフローノード名指定**: ノードIDの代わりに日本語名でパラメータ指定が可能
- **完全なデータ管理**: 全生成結果と設定をSQLiteデータベースに保存
- **テストモード**: 実際のComfyUIサーバーなしでの動作確認

## 🚀 クイックスタート

### 前提条件

- Python 3.9以上
- uv（推奨）またはpip

### インストールと実行

```bash
# 1. 環境セットアップ
make setup

# 2. テストモードで動作確認
make run-test

# 3. テスト実行
make test
```

## 📁 プロジェクト構造

```
comfyv/
├── core/cli.py                # CLIエントリーポイント（comfyv）
├── core/                      # コアモジュール
│   ├── config.py             # 設定管理
│   ├── database.py           # データベース操作
│   ├── api_client.py         # ComfyUI API通信
│   ├── prompt_resolver.py    # プロンプト解決
│   ├── workflow_loader.py    # ワークフローローダー
│   ├── service_container.py  # 依存性注入
│   ├── mock_services.py      # テスト用モック
│   └── executors/            # 実行エンジン
│       ├── base_executor.py
│       ├── grid_search_executor.py
│       └── sequence_executor.py
├── configs/                   # 設定ファイル
│   ├── connection_config.yaml
│   ├── jobs/                 # ジョブ設定
│   ├── workflows/            # ワークフローファイル
│   └── prompts/              # プロンプト設定
├── tests/                    # テストスィート
├── results/                  # 実行結果
│   ├── images/              # 生成画像
│   └── index.sqlite         # データベース
└── templates/               # レポートテンプレート
```

## 💻 使用方法

### 基本的な実行

```bash
# グリッドサーチジョブを実行
uv run comfyv run configs/jobs/example.yaml

# テストモードで実行（ComfyUIサーバー不要）
uv run comfyv run configs/jobs/test.yaml --test-mode --verbose
```

### 設定ファイル例

#### グリッドサーチ設定

```yaml
job_name: "lora_comparison"
job_type: "grid_search"
base_workflow: "workflows/api_base.json"

variables:
  - node_id: 116
    input_name: "lora_name_1"
    values: ["lora_a.safetensors", "lora_b.safetensors"]
  - node_id: 171
    input_name: "seed"
    values: [12345, 67890]

# または、ノード名での指定も可能
# variables:
#   - node_id: "💊 CR LoRA Stack"
#     input_name: "lora_name_1"
#     values: ["lora_a.safetensors", "lora_b.safetensors"]
#   - node_id: "KSampler"
#     input_name: "seed"
#     values: [12345, 67890]

placeholders:
  character: ["Alice", "Bob"]
  style: ["anime", "realistic"]
```

#### シーケンス設定

```yaml
job_name: "prompt_variations"
job_type: "sequence"

prompts:
  - template: "A portrait of {character}"
    runs: 3
  - template: "A landscape with __weather__"
    runs: 2
```

## 🧪 テスト

### テスト実行

```bash
# 全テスト実行
make test

# 特定のテストのみ
make test-config      # 設定テスト
make test-executors   # 実行エンジンテスト
make test-integration # 統合テスト
```

### テストカバレッジ

```bash
# カバレッジレポート付きテスト
make test-cov

# HTMLレポート確認
open htmlcov/index.html
```

## 🛠️ 開発

### 開発環境セットアップ

```bash
# 開発用依存関係をインストール
make install-dev

# コードフォーマット
make format

# リンター実行
make lint
```

### uv環境での開発

詳細な開発手順については [README-uv.md](README-uv.md) を参照してください。

## 📊 アーキテクチャ

ComfyVは以下の設計原則に基づいています：

- **ストラテジーパターン**: 実行方法（GridSearch/Sequence）を柔軟に切り替え
- **依存性注入**: テスト可能性とモジュール性を重視
- **設定駆動**: YAMLファイルによる宣言型設定
- **データ永続化**: 完全な再現性を保証するデータベース管理

## 🔧 設定

### 接続設定 (connection_config.yaml)

```yaml
server_address: "http://localhost:8188"
```

### ジョブ設定

- **job_type**: "grid_search" または "sequence"
- **variables**: グリッドサーチ用の変数定義
- **prompts**: シーケンス用のプロンプトリスト
- **placeholders**: プロンプト内の動的置換

### ノード指定方法

**従来の方式（ノードID指定）:**
```yaml
variables:
  - node_id: 116
    input_name: "lora_name_1"
    values: ["value1", "value2"]
```

**新しい方式（ノード名指定）:**
```yaml
variables:
  - node_id: "💊 CR LoRA Stack"
    input_name: "lora_name_1"
    values: ["value1", "value2"]
```

どちらの方式も利用可能で、混在させることもできます。ノード名は `_meta.title` フィールドから自動的に取得されます。

## 📈 データベース

生成された全ての画像とメタデータは `results/index.sqlite` に保存されます：

- **jobs**: ジョブ実行履歴
- **images**: 画像とパラメータの詳細記録

## 🤝 貢献

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチをプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## 📝 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 🙏 謝辞

- ComfyUIプロジェクトとコミュニティ
- 各種オープンソースライブラリの開発者の皆様

---

詳細な技術仕様については [documents/design_and_specification.md](documents/design_and_specification.md) を参照してください。  
設定ファイルとプロンプト記法の使い方は [documents/config_and_prompt_guide.md](documents/config_and_prompt_guide.md) にまとめています。
