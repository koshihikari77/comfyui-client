"""
PromptFormatter包括的テストスイート

PromptFormatter全機能の統合テスト
PlaceholderSubstitutor, WildcardSubstitutor, TagFilterテスト構成を参考にした包括的なテスト
"""

import pytest
import logging
from random import Random
from ordered_set import OrderedSet
from unittest.mock import patch

from core.resolver.formatter import PromptFormatter
from core.resolver.context import ResolverContext
from core.resolver.exceptions import PromptFormatterError


class TestPromptFormatterBasic:
    """基本機能のテスト"""
    
    def setup_method(self):
        """テスト用コンテキスト準備"""
        self.context = ResolverContext(
            presets={},
            wildcards={},
            rng=Random(42),
            locale=",",
            strict_level="warn"
        )
        self.formatter = PromptFormatter(self.context)
    
    def test_basic_tagset_conversion(self):
        """基本的なTagSet変換"""
        tagset = OrderedSet(["masterpiece", "best quality", "detailed"])
        result = self.formatter.format_tagset(tagset)
        
        assert result == "masterpiece, best quality, detailed"
        assert isinstance(result, str)
    
    def test_order_preservation(self):
        """順序保持確認"""
        tagset = OrderedSet(["third", "first", "second"])
        result = self.formatter.format_tagset(tagset)
        
        # OrderedSetの挿入順序が保持される
        assert result == "third, first, second"
    
    def test_empty_tagset_handling(self):
        """空TagSetの処理"""
        empty_tagset = OrderedSet()
        result = self.formatter.format_tagset(empty_tagset)
        
        assert result == ""
    
    def test_single_tag_handling(self):
        """単一タグの処理"""
        single_tagset = OrderedSet(["masterpiece"])
        result = self.formatter.format_tagset(single_tagset)
        
        # 単一タグは区切り文字なし
        assert result == "masterpiece"
    
    def test_duplicate_handling(self):
        """重複処理確認（OrderedSetレベル）"""
        # OrderedSetは重複を自動除去
        tagset = OrderedSet(["tag1", "tag2", "tag1", "tag3"])
        result = self.formatter.format_tagset(tagset)
        
        # 重複は既に除去されている
        assert result == "tag1, tag2, tag3"
        assert result.count("tag1") == 1


class TestPromptFormatterLocales:
    """locale機能テスト"""
    
    def setup_method(self):
        """テスト用コンテキスト準備"""
        self.base_context = ResolverContext(
            presets={},
            wildcards={},
            rng=Random(42),
            strict_level="warn"
        )
    
    def test_comma_locale_default(self):
        """カンマ区切り（デフォルト）"""
        context = self.base_context.model_copy(update={"locale": ","})
        formatter = PromptFormatter(context)
        
        tagset = OrderedSet(["tag1", "tag2", "tag3"])
        result = formatter.format_tagset(tagset)
        
        assert result == "tag1, tag2, tag3"
    
    def test_japanese_locale(self):
        """全角読点区切り"""
        context = self.base_context.model_copy(update={"locale": "、"})
        formatter = PromptFormatter(context)
        
        tagset = OrderedSet(["タグ1", "タグ2", "タグ3"])
        result = formatter.format_tagset(tagset)
        
        assert result == "タグ1、タグ2、タグ3"
    
    def test_semicolon_locale(self):
        """セミコロン区切り"""
        context = self.base_context.model_copy(update={"locale": ";"})
        formatter = PromptFormatter(context)
        
        tagset = OrderedSet(["tag1", "tag2", "tag3"])
        result = formatter.format_tagset(tagset)
        
        assert result == "tag1;tag2;tag3"
    
    def test_mixed_locale_content(self):
        """混合言語コンテンツ"""
        context = self.base_context.model_copy(update={"locale": ","})
        formatter = PromptFormatter(context)
        
        tagset = OrderedSet(["masterpiece", "タグ", "🎨", "français", "тест"])
        result = formatter.format_tagset(tagset)
        
        expected = "masterpiece, タグ, 🎨, français, тест"
        assert result == expected


class TestPromptFormatterErrorHandling:
    """エラーハンドリング機能テスト"""
    
    def setup_method(self):
        """テスト用コンテキスト準備"""
        self.base_context = ResolverContext(
            presets={},
            wildcards={},
            rng=Random(42),
            locale=","
        )
    
    def test_unsupported_locale_error_level(self):
        """サポート外locale（errorレベル）"""
        context = self.base_context.model_copy(update={
            "locale": "invalid",
            "strict_level": "error"
        })
        formatter = PromptFormatter(context)
        
        tagset = OrderedSet(["tag1", "tag2"])
        
        with pytest.raises(PromptFormatterError) as exc_info:
            formatter.format_tagset(tagset)
        
        assert "Unsupported locale: invalid" in str(exc_info.value)
        assert exc_info.value.tagset_length == 2
    
    def test_unsupported_locale_warn_fallback(self, caplog):
        """サポート外locale（warnレベル・フォールバック）"""
        context = self.base_context.model_copy(update={
            "locale": "invalid",
            "strict_level": "warn"
        })
        formatter = PromptFormatter(context)
        
        tagset = OrderedSet(["tag1", "tag2"])
        
        with caplog.at_level(logging.WARNING):
            result = formatter.format_tagset(tagset)
        
        # フォールバック確認
        assert result == "tag1, tag2"
        
        # 警告ログ確認
        assert "Unsupported locale 'invalid', using ',' as fallback" in caplog.text
    
    def test_unsupported_locale_soft_silent(self):
        """サポート外locale（softレベル・サイレント）"""
        context = self.base_context.model_copy(update={
            "locale": "invalid",
            "strict_level": "soft"
        })
        formatter = PromptFormatter(context)
        
        tagset = OrderedSet(["tag1", "tag2"])
        result = formatter.format_tagset(tagset)
        
        # フォールバック確認（ログなし）
        assert result == "tag1, tag2"
    
    def test_format_processing_error_handling(self):
        """フォーマット処理エラーのハンドリング"""
        context = self.base_context.model_copy(update={"strict_level": "error"})
        formatter = PromptFormatter(context)
        
        # 強制的にエラーを発生させる（内部メソッドでエラー）
        with patch.object(formatter, '_tagset_to_list', side_effect=RuntimeError("Forced error")):
            tagset = OrderedSet(["tag1", "tag2"])
            
            with pytest.raises(PromptFormatterError) as exc_info:
                formatter.format_tagset(tagset)
            
            assert "Failed to format TagSet" in str(exc_info.value)
            assert exc_info.value.tagset_length == 2


class TestPromptFormatterPerformance:
    """性能・スケーラビリティテスト"""
    
    def setup_method(self):
        """テスト用コンテキスト準備"""
        self.context = ResolverContext(
            presets={},
            wildcards={},
            rng=Random(42),
            locale=",",
            strict_level="warn"
        )
        self.formatter = PromptFormatter(self.context)
    
    def test_large_tagset_performance(self):
        """大規模TagSetの処理性能"""
        # 1000タグの処理
        large_tagset = OrderedSet([f"tag_{i:04d}" for i in range(1000)])
        
        result = self.formatter.format_tagset(large_tagset)
        
        # 結果の整合性確認
        tags = result.split(", ")
        assert len(tags) == 1000
        assert tags[0] == "tag_0000"
        assert tags[999] == "tag_0999"
    
    def test_very_long_tags(self):
        """非常に長いタグの処理"""
        long_tag = "a" * 5000
        very_long_tag = "b" * 10000
        
        tagset = OrderedSet(["short", long_tag, very_long_tag, "end"])
        result = self.formatter.format_tagset(tagset)
        
        # 長いタグが正しく処理されることを確認
        assert long_tag in result
        assert very_long_tag in result
        assert result.count(", ") == 3  # 正しい区切り数
    
    def test_unicode_performance(self):
        """Unicode文字処理性能"""
        unicode_tagset = OrderedSet([
            "🎨🌟🎯🎪🎭",  # 絵文字
            "中文标签测试内容",  # 中国語
            "Тест на русском языке",  # ロシア語
            "عربي اختبار المحتوى",  # アラビア語
            "日本語のタグテスト内容"  # 日本語
        ])
        
        result = self.formatter.format_tagset(unicode_tagset)
        
        # 全Unicode文字が保持される
        for tag in unicode_tagset:
            assert tag in result
    
    def test_memory_efficiency(self):
        """メモリ効率性テスト"""
        # 中規模TagSetで複数回処理
        tagset = OrderedSet([f"tag_{i}" for i in range(100)])
        
        results = []
        for _ in range(100):
            result = self.formatter.format_tagset(tagset)
            results.append(result)
        
        # 全結果が同一であることを確認
        assert all(r == results[0] for r in results)
        assert len(results[0].split(", ")) == 100


class TestPromptFormatterEdgeCases:
    """エッジケース・境界値テスト"""
    
    def setup_method(self):
        """テスト用コンテキスト準備"""
        self.context = ResolverContext(
            presets={},
            wildcards={},
            rng=Random(42),
            locale=",",
            strict_level="warn"
        )
        self.formatter = PromptFormatter(self.context)
    
    def test_whitespace_tags(self):
        """空白文字を含むタグの処理"""
        whitespace_tagset = OrderedSet([
            "", "  ", "\t", "\n", "\r\n", 
            "tag with spaces", "  leading spaces", "trailing spaces  "
        ])
        
        result = self.formatter.format_tagset(whitespace_tagset)
        
        # 全ての空白文字パターンが保持される
        tags = result.split(", ")
        assert "" in tags
        assert "  " in tags
        assert "\t" in tags
        assert "tag with spaces" in tags
    
    def test_special_characters(self):
        """特殊文字を含むタグの処理"""
        special_tagset = OrderedSet([
            "comma,test", "semicolon;test", "quote\"test", 
            "apostrophe'test", "backslash\\test", "newline\ntest",
            "tab\ttest", "unicode\u00a0test"
        ])
        
        result = self.formatter.format_tagset(special_tagset)
        
        # 特殊文字がエスケープされずに保持される
        for tag in special_tagset:
            assert tag in result
    
    def test_extreme_empty_cases(self):
        """極端な空ケースの処理"""
        # 完全に空のTagSet
        empty_set = OrderedSet()
        assert self.formatter.format_tagset(empty_set) == ""
        
        # 空文字列のみ
        empty_string_set = OrderedSet([""])
        assert self.formatter.format_tagset(empty_string_set) == ""
        
        # 空白文字のみ
        whitespace_set = OrderedSet([" ", "\t", "\n"])
        result = self.formatter.format_tagset(whitespace_set)
        assert result == " , \t, \n"
    
    def test_locale_boundary_values(self):
        """locale境界値テスト"""
        tagset = OrderedSet(["a", "b"])
        
        # 各サポート済みlocaleの境界値確認
        test_cases = [
            (",", "a, b"),
            ("、", "a、b"),
            (";", "a;b")
        ]
        
        for locale_val, expected in test_cases:
            context = self.context.model_copy(update={"locale": locale_val})
            formatter = PromptFormatter(context)
            result = formatter.format_tagset(tagset)
            assert result == expected


class TestPromptFormatterIntegration:
    """統合・互換性テスト"""
    
    def setup_method(self):
        """テスト用コンテキスト準備"""
        self.context = ResolverContext(
            presets={},
            wildcards={},
            rng=Random(42),
            locale=",",
            strict_level="warn"
        )
        self.formatter = PromptFormatter(self.context)
    
    def test_v1_compatibility(self):
        """V1 PromptResolver互換性確認"""
        # V1形式の出力と同等になることを確認
        tagset = OrderedSet(["masterpiece", "best quality", "highly detailed"])
        result = self.formatter.format_tagset(tagset)
        
        # V1のカンマ+スペース形式
        expected = "masterpiece, best quality, highly detailed"
        assert result == expected
    
    def test_pipeline_integration_simulation(self):
        """パイプライン統合シミュレーション"""
        # 他ステージから受け取ったTagSetを想定
        pipeline_tagset = OrderedSet([
            "masterpiece", "best quality",  # PresetEvaluator由来
            "1girl", "happy",               # PlaceholderSubstitutor由来
            "blonde hair",                  # WildcardSubstitutor由来
            "detailed", "HDR"               # TagFilter後の残存タグ
        ])
        
        result = self.formatter.format_tagset(pipeline_tagset)
        
        expected = "masterpiece, best quality, 1girl, happy, blonde hair, detailed, HDR"
        assert result == expected
    
    def test_real_world_scenario(self):
        """実世界シナリオテスト"""
        real_world_tagset = OrderedSet([
            "masterpiece", "best quality", "ultra-detailed",
            "1girl", "solo", "long hair", "blonde hair", "blue eyes",
            "school uniform", "sitting", "classroom", "sunlight",
            "depth of field", "bokeh", "professional lighting"
        ])
        
        result = self.formatter.format_tagset(real_world_tagset)
        
        # 現実的なプロンプトの長さと構造確認
        assert len(result) > 100  # 合理的な長さ
        assert result.count(", ") == len(real_world_tagset) - 1  # 正しい区切り数
        
        # キーワードが保持されることを確認
        assert "masterpiece" in result
        assert "1girl" in result
        assert "professional lighting" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])