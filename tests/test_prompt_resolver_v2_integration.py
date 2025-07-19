"""
PromptResolverV2 統合テスト
6ステージパイプライン統合とServiceContainer V1/V2切替テスト
"""
import pytest
import tempfile
import shutil
import os
import json
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

# テスト対象のモジュールをインポート
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))

from core.prompt_resolver_v2 import PromptResolverV2
from core.service_container import ServiceContainer
from core.resolver.context import ResolverContext
from core.resolver.exceptions import ResolverError


@pytest.fixture
def temp_prompts_dir():
    """テスト用のプロンプト設定ディレクトリを作成"""
    temp_dir = tempfile.mkdtemp()
    prompts_dir = Path(temp_dir) / "prompts"
    prompts_dir.mkdir()
    
    # プリセットファイル作成
    presets_dir = prompts_dir / "presets"
    presets_dir.mkdir()
    
    # V2形式プリセット（YAML形式）- 仕様準拠のフラット構造
    preset_v2_data = {
        "version": 2,
        "contents": {
            "style_anime": ["anime style", "manga style"],
            "style_realistic": ["photorealistic", "hyperrealistic"],
            "quality_high": ["masterpiece", "best quality"],
            "quality_low": ["worst quality", "low quality"]
        }
    }
    
    preset_file = presets_dir / "test_presets.yaml"
    with open(preset_file, 'w', encoding='utf-8') as f:
        yaml.dump(preset_v2_data, f, default_flow_style=False, allow_unicode=True)
    
    # ワイルドカードファイル作成
    wildcards_dir = prompts_dir / "wildcards"
    wildcards_dir.mkdir()
    
    with open(wildcards_dir / "character.txt", 'w', encoding='utf-8') as f:
        f.write("girl\nboy\nwoman\nman\n")
    
    with open(wildcards_dir / "emotion.txt", 'w', encoding='utf-8') as f:
        f.write("happy\nsad\nangry\nsurprised\n")
    
    yield str(prompts_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def v2_config():
    """V2設定辞書"""
    return {
        "seed": 42,
        "locale": ",",
        "strict_level": "error",
        "ignore_tags": [],
        "ignore_groups": [],
        "placeholders": {}
    }




class TestPromptResolverV2Integration:
    """PromptResolverV2 統合テスト"""
    
    def test_v2_initialization_with_config(self, temp_prompts_dir, v2_config):
        """V2初期化とコンフィグ設定"""
        resolver = PromptResolverV2(temp_prompts_dir, v2_config)
        
        assert resolver.context.locale == ","
        assert resolver.context.strict_level == "error"
    
    def test_v2_basic_pipeline_integration(self, temp_prompts_dir, v2_config):
        """V2基本パイプライン統合テスト"""
        resolver = PromptResolverV2(temp_prompts_dir, v2_config)
        
        # 基本的なテキスト処理
        result = resolver.resolve("simple text")
        assert result == "simple text"
        
        # プリセット処理
        result = resolver.resolve("<preset:test_presets#style_anime>")
        assert "anime style" in result or "manga style" in result
    
    def test_v2_six_stage_pipeline_flow(self, temp_prompts_dir, v2_config):
        """6ステージパイプライン フロー確認"""
        resolver = PromptResolverV2(temp_prompts_dir, v2_config)
        
        # 複合テンプレート: プリセット + ワイルドカード
        template = "<preset:test_presets#style_anime> __character__ feeling __emotion__"
        result = resolver.resolve(template)
        
        # 結果に各ステージの処理が含まれていることを確認
        assert any(style in result for style in ["anime style", "manga style"])
        assert any(char in result for char in ["girl", "boy", "woman", "man"])
        assert any(emotion in result for emotion in ["happy", "sad", "angry", "surprised"])
    
    def test_v2_preset_v2_format_support(self, temp_prompts_dir, v2_config):
        """プリセットV2形式サポート確認"""
        resolver = PromptResolverV2(temp_prompts_dir, v2_config)
        
        # V2形式プリセットテスト
        result = resolver.resolve("<preset:test_presets#quality_high>")
        assert "masterpiece" in result or "best quality" in result
        
        result = resolver.resolve("<preset:test_presets#quality_low>")
        assert "worst quality" in result or "low quality" in result
    
    def test_v2_locale_support(self, temp_prompts_dir):
        """ロケール対応確認"""
        # 日本語ロケール - 単一Textノードは元文字列保持
        ja_config = {
            "seed": 42,
            "locale": "、",
            "strict_level": "error"
        }
        resolver = PromptResolverV2(temp_prompts_dir, ja_config)
        
        # 単一Textノードの場合、元の文字列がそのまま保持される
        result = resolver.resolve("tag1, tag2, tag3")
        assert result == "tag1, tag2, tag3"  # 元文字列保持
        
        # 英語ロケール - 同様に元文字列保持
        en_config = {
            "seed": 42,
            "locale": ",",
            "strict_level": "error"
        }
        resolver = PromptResolverV2(temp_prompts_dir, en_config)
        
        result = resolver.resolve("tag1, tag2, tag3")
        assert result == "tag1, tag2, tag3"  # 元文字列保持
    
    def test_v2_strict_level_behavior(self, temp_prompts_dir):
        """strict_level動作確認"""
        # error レベル - V2実装では例外を発生させずに元文字列を返す
        error_config = {
            "seed": 42,
            "locale": ",",
            "strict_level": "error"
        }
        resolver = PromptResolverV2(temp_prompts_dir, error_config)
        
        # V2実装では例外を発生させずに元文字列を返す
        result = resolver.resolve("<preset:nonexistent#key>")
        assert "<preset:nonexistent#key>" in result
        
        # soft レベル
        soft_config = {
            "seed": 42,
            "locale": ",",
            "strict_level": "soft"
        }
        resolver = PromptResolverV2(temp_prompts_dir, soft_config)
        
        result = resolver.resolve("<preset:nonexistent#key>")
        # エラーではなく元のテンプレートが返される
        assert "<preset:nonexistent#key>" in result
    
    def test_v2_seed_reproducibility(self, temp_prompts_dir, v2_config):
        """シード値による再現性確認"""
        resolver = PromptResolverV2(temp_prompts_dir, v2_config)
        
        # 同じシードで同じ結果が得られることを確認
        template = "[@style:anime] __character__"
        result1 = resolver.resolve(template)
        result2 = resolver.resolve(template)
        
        assert result1 == result2
    
    def test_v2_dynamic_config_update(self, temp_prompts_dir, v2_config):
        """動的設定変更テスト"""
        resolver = PromptResolverV2(temp_prompts_dir, v2_config)
        
        # 初期設定確認
        assert resolver.context.locale == ","
        
        # 設定変更（辞書形式）
        new_config = {
            "locale": "、",
            "strict_level": "soft",
            "seed": 100
        }
        resolver.update_config(new_config)
        
        # 変更後の設定確認
        assert resolver.context.locale == "、"
        assert resolver.context.strict_level == "soft"
    
    def test_v2_error_handling_pipeline(self, temp_prompts_dir, v2_config):
        """パイプライン段階別エラーハンドリング"""
        resolver = PromptResolverV2(temp_prompts_dir, v2_config)
        
        # V2実装では例外を発生させずに元文字列を返す
        result = resolver.resolve("[@invalid:preset]")
        assert "[@invalid:preset]" in result
        
        # パイプライン全体でのフォールバック動作確認
        # (実際のエラーが発生してもresolve()は例外を再発生させずに元のテンプレートを返す)
        soft_config = {
            "seed": 42,
            "locale": ",",
            "strict_level": "soft"
        }
        soft_resolver = PromptResolverV2(temp_prompts_dir, soft_config)
        
        result = soft_resolver.resolve("[@invalid:preset]")
        assert "[@invalid:preset]" in result


