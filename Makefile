# ComfyV Makefile
# uvとテストのコマンド集

.PHONY: help setup test test-unit test-integration test-cov clean install-dev

# デフォルトターゲット（ヘルプを表示）
help:
	@echo "ComfyV Development Commands:"
	@echo ""
	@echo "  make setup         - uv環境をセットアップ"
	@echo "  make install       - 基本依存関係をインストール"
	@echo "  make install-dev   - 開発用依存関係をインストール"
	@echo "  make install-test  - テスト用依存関係をインストール"
	@echo ""
	@echo "  make test          - 全てのテストを実行"
	@echo "  make test-unit     - ユニットテストのみ実行"
	@echo "  make test-integration - 統合テストのみ実行"
	@echo "  make test-cov      - カバレッジ付きでテスト実行"
	@echo "  make test-fast     - 高速テスト（カバレッジなし）"
	@echo ""
	@echo "  make clean         - テスト成果物をクリーンアップ"
	@echo "  make format        - コードフォーマット"
	@echo "  make lint          - リンターチェック"
	@echo ""

# uv環境のセットアップ（依存関係のみ）
setup:
	@echo "🚀 Setting up uv environment..."
	uv sync --no-editable

# 基本依存関係のインストール
install:
	@echo "📦 Installing basic dependencies with uv..."
	uv sync --no-editable

# 開発用依存関係のインストール  
install-dev:
	@echo "📦 Installing development dependencies with uv..."
	uv sync --extra dev --no-editable

# テスト用依存関係のインストール
install-test:
	@echo "📦 Installing test dependencies with uv..."
	uv sync --extra test --no-editable

# 全テストを実行
test: install-test
	@echo "🧪 Running all tests with uv..."
	uv run pytest

# ユニットテストのみ実行
test-unit: install-test
	@echo "🧪 Running unit tests with uv..."
	uv run pytest -m "unit or not integration" tests/ --ignore=tests/integration/

# 統合テストのみ実行
test-integration: install-test
	@echo "🧪 Running integration tests with uv..."
	uv run pytest -m integration tests/integration/

# カバレッジ付きテスト実行
test-cov: install-test
	@echo "🧪 Running tests with coverage report using uv..."
	uv run pytest --cov=core --cov-report=html --cov-report=term-missing

# 高速テスト（カバレッジレポートなし）
test-fast: install-test
	@echo "🧪 Running fast tests with uv..."
	uv run pytest --no-cov -x

# モックサービステスト（開発中に便利）
test-mock: install-test
	@echo "🧪 Running mock service tests with uv..."
	uv run pytest tests/test_mock_services.py -v

# 特定のテストファイルを実行
test-config: install-test
	@echo "🧪 Running config tests with uv..."
	uv run pytest tests/test_config.py -v

test-executors: install-test
	@echo "🧪 Running executor tests with uv..."
	uv run pytest tests/test_executors.py -v

# ComfyV CLI統合テスト（テストモード使用）
test-main: install-test
	@echo "🧪 Running main integration tests with uv..."
	uv run pytest tests/integration/test_main_integration.py -v

# 実際にcomfyvを実行（テストモード）
run-test: install
	@echo "🚀 Running ComfyV in test mode with uv..."
	uv run comfyv run configs/jobs/test.yaml --test-mode --verbose

# テスト成果物のクリーンアップ
clean:
	@echo "🧹 Cleaning up test artifacts..."
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf __pycache__/
	rm -rf .uv_cache/
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +

# 継続的インテグレーション用
ci-test: install-test
	@echo "🧪 Running CI tests with uv..."
	uv run pytest --cov=core --cov-report=xml --cov-fail-under=80

# コードフォーマット
format: install-dev
	@echo "🎨 Formatting code with uv..."
	uv run black .
	uv run isort .

# リンターチェック
lint: install-dev
	@echo "🔍 Running linter checks with uv..."
	uv run flake8 .
	uv run mypy core/

# デバッグ用のテスト実行（詳細出力）
test-debug: install-test
	@echo "🧪 Running tests in debug mode with uv..."
	uv run pytest -v -s --tb=long

# 特定のテストパターンで実行
test-pattern: install-test
	@echo "🧪 Running tests matching pattern: $(PATTERN) with uv..."
	uv run pytest -k "$(PATTERN)" -v

# パフォーマンステスト実行
test-perf: install-test
	@echo "🧪 Running performance tests with uv..."
	uv run pytest --benchmark-only

# プロジェクト情報表示
info:
	@echo "📋 Project Information:"
	@echo "Python version: $(shell uv run python --version)"
	@echo "UV version: $(shell uv --version)"
	@echo "Project dependencies:"
	@uv tree --depth 1 
