# ComfyV - uv環境での開発ガイド

## 🚀 クイックスタート

uvを使用してComfyVプロジェクトを設定・開発する手順です。

### 1. 環境のセットアップ

```bash
# プロジェクトルートに移動
cd /path/to/comfyv

# uv環境をセットアップ（基本依存関係のインストール）
make setup

# または直接uvコマンドで
uv sync
```

### 2. テスト実行

```bash
# テスト用依存関係をインストールしてテスト実行
make test

# または個別に
make install-test
make test-fast
```

### 3. 実際の実行（テストモード）

```bash
# テストモードでComfyVを実行
make run-test

# または直接
uv run python main.py --job-config configs/jobs/test.yaml --test-mode --verbose
```

## 📦 依存関係管理

### pyproject.tomlベースの管理

このプロジェクトは`pyproject.toml`を使用してuvでの依存関係を管理しています。

```toml
# 基本依存関係
dependencies = [
    "pyyaml>=6.0.0",
    "jinja2>=3.1.0", 
    "requests>=2.28.0",
    "websocket-client>=1.4.0",
]
```

### オプション依存関係

```bash
# テスト用依存関係
uv sync --extra test

# 開発用依存関係（テスト+フォーマッター+リンター）
uv sync --extra dev
```

## 🧪 テスト実行コマンド

### 基本的なテスト

```bash
# 全テスト実行
make test

# ユニットテストのみ
make test-unit

# 統合テストのみ
make test-integration

# カバレッジレポート付き
make test-cov
```

### 特定のテストファイル

```bash
# 設定テスト 
make test-config

# モックサービステスト
make test-mock

# Executorテスト
make test-executors

# メイン統合テスト
make test-main
```

### デバッグ・開発用

```bash
# 詳細出力でテスト実行
make test-debug

# 高速テスト（カバレッジなし）
make test-fast

# 特定パターンのテスト
make test-pattern PATTERN="test_config"
```

## 🛠️ 開発ツール

### コードフォーマット

```bash
# Black + isortでフォーマット
make format
```

### リンター

```bash
# flake8 + mypyでチェック
make lint
```

### プロジェクト情報確認

```bash
# 環境情報の表示
make info
```

## 📂 プロジェクト構造（uv関連ファイル）

```
comfyv/
├── pyproject.toml          # uv/pip用プロジェクト設定
├── requirements.txt        # 基本依存関係（従来のpip用）
├── requirements-test.txt   # テスト依存関係（従来のpip用）
├── Makefile               # uv対応コマンド集
├── pytest.ini            # pytest設定（pyproject.tomlから移行可能）
└── README-uv.md           # このファイル
```

## 🔧 トラブルシューティング

### よくある問題と解決方法

#### 1. jinja2が見つからないエラー

```bash
# 依存関係を再インストール
uv sync --reinstall
```

#### 2. テストが実行されない

```bash
# テスト用依存関係を確実にインストール
make install-test

# または
uv sync --extra test
```

#### 3. パスの問題

```bash
# 現在のプロジェクトルートを確認
pwd
# /path/to/comfyv である必要があります

# プロジェクトルートに移動してから実行
cd /path/to/comfyv
make test
```

#### 4. uvのキャッシュ問題

```bash
# uvのキャッシュをクリア
uv cache clean

# プロジェクトを再セットアップ
make clean
make setup
```

## 🚀 開発ワークフロー

### 推奨の開発手順

1. **初回セットアップ**
   ```bash
   make setup
   make install-dev
   ```

2. **機能開発**
   ```bash
   # コード修正後
   make format      # フォーマット
   make lint        # リンター
   make test-fast   # 高速テスト
   ```

3. **完全なテスト**
   ```bash
   make test-cov    # カバレッジ付き全テスト
   ```

4. **動作確認**
   ```bash
   make run-test    # 実際の実行テスト
   ```

### CI/CD環境での実行

```bash
# 継続的インテグレーション用
make ci-test
```

## 📊 パフォーマンス

uvを使用することで、従来のpip + venvに比べて：

- **依存関係解決**: 10-100x高速
- **インストール**: 2-10x高速
- **環境管理**: より確実で再現性が高い

## 📋 チェックリスト

開発前の確認事項：

- [ ] uvがインストールされている (`uv --version`)
- [ ] プロジェクトルートにいる (`pwd` で確認)
- [ ] `make setup` が成功している
- [ ] `make test` が通る

これでuvを使用したComfyV開発環境が整いました！🎉 