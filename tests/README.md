# ComfyV テストスィート

このディレクトリには、ComfyV（Comfy Verifier）プロジェクトの包括的なテストが含まれています。

## テスト構成

```
tests/
├── conftest.py              # pytest設定とフィクスチャ
├── test_config.py           # Configクラスのユニットテスト
├── test_mock_services.py    # MockServiceのテスト
├── test_executors.py        # Executorクラスのテスト
├── integration/             # 統合テスト
│   ├── __init__.py
│   └── test_main_integration.py  # comfyv CLI の統合テスト
└── README.md               # このファイル
```

## テストの種類

### ユニットテスト
- **test_config.py**: 設定ファイルの読み込み、バリデーション
- **test_mock_services.py**: モックサービスの動作確認
- **test_executors.py**: GridSearchExecutor, SequenceExecutorの機能テスト

### 統合テスト
- **test_main_integration.py**: `comfyv` CLIを通じたエンドツーエンドテスト

## テスト実行方法

### 1. 依存関係のインストール

```bash
# テスト用パッケージをインストール
make install-test

# または直接
pip install -r requirements-test.txt
```

### 2. テスト実行

```bash
# 全テストを実行
make test

# ユニットテストのみ
make test-unit

# 統合テストのみ
make test-integration

# カバレッジレポート付きで実行
make test-cov

# 高速実行（カバレッジなし）
make test-fast
```

### 3. 特定のテストファイルを実行

```bash
# 設定テストのみ
make test-config

# モックサービステストのみ
make test-mock

# Executorテストのみ
make test-executors

# メイン統合テストのみ
make test-main
```

### 4. デバッグ用実行

```bash
# 詳細出力でテスト実行
make test-debug

# 特定のパターンでテスト実行
make test-pattern PATTERN="test_config"
```

## テスト設計方針

### モックサービスの利用
- 実際のComfyUIサーバーに依存しないテスト設計
- `MockServiceContainer`を使用した依存性注入
- テストの独立性とスピードを重視

### フィクスチャの活用
- `conftest.py`で共通のテストデータを定義
- 一時ディレクトリを使用したファイル操作テスト
- テスト間でのデータ汚染を防止

### アサーション戦略
- 各機能の正常ケースと異常ケースをカバー
- エラーメッセージの検証
- 内部状態の確認

## カバレッジ目標

- **最小カバレッジ**: 80%
- **目標カバレッジ**: 90%以上
- HTMLレポートは `htmlcov/index.html` で確認可能

## 継続的インテグレーション

```bash
# CI環境でのテスト実行
make ci-test
```

## テスト作成のガイドライン

### 新しいテストを追加する際の注意点

1. **命名規則に従う**
   - テストファイル: `test_*.py`
   - テストクラス: `Test*`
   - テストメソッド: `test_*`

2. **適切なマーカーを使用**
   ```python
   @pytest.mark.unit
   def test_unit_functionality():
       pass
   
   @pytest.mark.integration
   def test_integration_workflow():
       pass
   ```

3. **フィクスチャを活用**
   - 共通のセットアップは `conftest.py` に定義
   - テスト固有のデータは各テストファイル内に

4. **モックの適切な使用**
   - 外部依存（ファイルシステム、ネットワーク）はモック化
   - `MockServiceContainer`を積極活用

### テストケースの考慮事項

- **正常ケース**: 期待通りの動作を確認
- **異常ケース**: エラーハンドリングを確認
- **境界値**: エッジケースでの動作を確認
- **設定パターン**: 様々な設定での動作を確認

## トラブルシューティング

### よくある問題

1. **パスの問題**
   - テスト実行時は常にプロジェクトルートから実行
   - フィクスチャで一時ディレクトリを使用

2. **依存関係の問題**
   - `requirements-test.txt` の更新を確認
   - 仮想環境の使用を推奨

3. **モックの問題**
   - `MockServiceContainer` の状態リセットを確認
   - フィクスチャのスコープを適切に設定

## テスト実行例

```bash
# プロジェクトルートで実行
cd /path/to/comfyv

# すべてのテスト実行（推奨）
make test

# 出力例:
# 📦 Installing test dependencies...
# 🧪 Running all tests...
# ======================= test session starts ========================
# collected 25 items
# 
# tests/test_config.py ........                              [ 32%]
# tests/test_mock_services.py ..........                     [ 72%]
# tests/test_executors.py ......                             [ 96%]
# tests/integration/test_main_integration.py .               [100%]
# 
# ======================= 25 passed in 2.34s ======================
```

このテストスィートにより、ComfyVプロジェクトの品質と信頼性を継続的に保証できます。 
