"""
PromptFormatter エラーハンドリングテスト

Phase2用のエラーハンドリング・strict_level対応テスト
"""

import pytest
import logging
from random import Random
from ordered_set import OrderedSet
from unittest.mock import patch

from core.resolver.formatter import PromptFormatter
from core.resolver.context import ResolverContext
from core.resolver.exceptions import PromptFormatterError


class TestPromptFormatterErrorHandling:
    """PromptFormatterエラーハンドリングのテスト"""
    
    def setup_method(self):
        """テスト用コンテキスト準備"""
        self.base_context = ResolverContext(
            presets={},
            wildcards={},
            rng=Random(42),
            locale=","
        )
    
    def test_unsupported_locale_error_strict(self):
        """サポート外locale（strict_level=error）"""
        context = self.base_context.model_copy(update={
            "locale": "@",  # サポート外
            "strict_level": "error"
        })
        formatter = PromptFormatter(context)
        
        tagset = OrderedSet(["tag1", "tag2"])
        
        with pytest.raises(PromptFormatterError) as exc_info:
            formatter.format_tagset(tagset)
        
        assert "Unsupported locale: @" in str(exc_info.value)
        assert exc_info.value.tagset_length == 2
    
    def test_unsupported_locale_warn_fallback(self, caplog):
        """サポート外locale（strict_level=warn）"""
        context = self.base_context.model_copy(update={
            "locale": "@",  # サポート外
            "strict_level": "warn"
        })
        formatter = PromptFormatter(context)
        
        tagset = OrderedSet(["tag1", "tag2"])
        
        with caplog.at_level(logging.WARNING):
            result = formatter.format_tagset(tagset)
        
        # フォールバック処理確認
        assert result == "tag1, tag2"  # ", "でフォールバック
        
        # 警告ログ確認
        assert "Unsupported locale '@', using ',' as fallback" in caplog.text
    
    def test_unsupported_locale_soft_silent(self, caplog):
        """サポート外locale（strict_level=soft）"""
        context = self.base_context.model_copy(update={
            "locale": "@",  # サポート外
            "strict_level": "soft"
        })
        formatter = PromptFormatter(context)
        
        tagset = OrderedSet(["tag1", "tag2"])
        
        with caplog.at_level(logging.WARNING):
            result = formatter.format_tagset(tagset)
        
        # フォールバック処理確認
        assert result == "tag1, tag2"  # ", "でフォールバック
        
        # 警告ログなし
        assert "Unsupported locale" not in caplog.text
    
    def test_format_error_strict_error(self):
        """フォーマット処理エラー（strict_level=error）"""
        context = self.base_context.model_copy(update={"strict_level": "error"})
        formatter = PromptFormatter(context)
        
        # 強制的にエラーを発生させる
        with patch.object(formatter, '_tagset_to_list', side_effect=RuntimeError("Test error")):
            tagset = OrderedSet(["tag1"])
            
            with pytest.raises(PromptFormatterError) as exc_info:
                formatter.format_tagset(tagset)
            
            assert "Failed to format TagSet" in str(exc_info.value)
            assert "Test error" in str(exc_info.value)
            assert exc_info.value.tagset_length == 1
    
    def test_format_error_warn_fallback(self, caplog):
        """フォーマット処理エラー（strict_level=warn）"""
        context = self.base_context.model_copy(update={"strict_level": "warn"})
        formatter = PromptFormatter(context)
        
        with patch.object(formatter, '_tagset_to_list', side_effect=RuntimeError("Test error")):
            tagset = OrderedSet(["tag1"])
            
            with caplog.at_level(logging.WARNING):
                result = formatter.format_tagset(tagset)
            
            # 空文字列フォールバック
            assert result == ""
            
            # 警告ログ確認
            assert "PromptFormatter error, returning empty string" in caplog.text
            assert "Test error" in caplog.text
    
    def test_format_error_soft_silent(self, caplog):
        """フォーマット処理エラー（strict_level=soft）"""
        context = self.base_context.model_copy(update={"strict_level": "soft"})
        formatter = PromptFormatter(context)
        
        with patch.object(formatter, '_tagset_to_list', side_effect=RuntimeError("Test error")):
            tagset = OrderedSet(["tag1"])
            
            with caplog.at_level(logging.WARNING):
                result = formatter.format_tagset(tagset)
            
            # 空文字列フォールバック
            assert result == ""
            
            # WARNING以上のPromptFormatterメッセージなし
            warning_messages = [rec.message for rec in caplog.records if rec.levelno >= logging.WARNING and "PromptFormatter error" in rec.message]
            assert len(warning_messages) == 0
    
    def test_normal_operation_no_errors(self):
        """通常動作時のエラーハンドリング非活性化"""
        context = self.base_context.model_copy(update={"strict_level": "error"})
        formatter = PromptFormatter(context)
        
        tagset = OrderedSet(["tag1", "tag2"])
        
        # 正常に動作することを確認
        result = formatter.format_tagset(tagset)
        assert result == "tag1, tag2"


class TestPromptFormatterEdgeCases:
    """PromptFormatterエッジケースのテスト"""
    
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
    
    def test_very_large_tagset(self):
        """大量TagSetの処理"""
        large_tagset = OrderedSet([f"tag_{i:04d}" for i in range(1000)])
        
        result = self.formatter.format_tagset(large_tagset)
        
        # 結果の長さと内容確認
        tags = result.split(", ")
        assert len(tags) == 1000
        assert tags[0] == "tag_0000"
        assert tags[999] == "tag_0999"
    
    def test_unicode_special_characters(self):
        """Unicode・特殊文字の詳細処理"""
        special_tagset = OrderedSet([
            "タグ1", "标签2", "тег3", "🎨", "🌟",
            "emoji_combo_🎯🎪", "spaces in tag", 
            "punctuation,test", "newline\ntest"
        ])
        
        result = self.formatter.format_tagset(special_tagset)
        
        # 全ての特殊文字が保持されることを確認
        assert "タグ1" in result
        assert "🎨" in result
        assert "emoji_combo_🎯🎪" in result
        assert "newline\ntest" in result
    
    def test_empty_and_whitespace_tags(self):
        """空文字列・空白文字タグの処理"""
        whitespace_tagset = OrderedSet([
            "", "  ", "\t", "\n", "valid_tag", "   spaced   "
        ])
        
        result = self.formatter.format_tagset(whitespace_tagset)
        
        # パターン判定結合の実際の動作確認
        # 実際の結果: '  \t, \n, valid_tag   spaced   '
        assert result == "  \t, \n, valid_tag   spaced   "
        
        tags = result.split(", ")
        assert "  \t" in tags  # 空文字列 + "  " + "\t"が直結合
        assert "\n" in tags
        assert "valid_tag   spaced   " in tags  # スペース末尾により直結合
    
    def test_long_individual_tags(self):
        """長いタグの処理"""
        long_tag = "a" * 10000  # 10,000文字のタグ
        tagset = OrderedSet(["short", long_tag, "another"])
        
        result = self.formatter.format_tagset(tagset)
        
        # 長いタグが適切に処理されることを確認
        assert long_tag in result
        assert result.count(", ") == 2  # 区切り文字が正しい数
    
    def test_locale_edge_cases(self):
        """locale関連のエッジケース"""
        # 空文字列locale
        context = self.context.model_copy(update={"locale": "", "strict_level": "soft"})
        formatter = PromptFormatter(context)
        
        tagset = OrderedSet(["tag1", "tag2"])
        result = formatter.format_tagset(tagset)
        
        # フォールバックが機能することを確認
        assert result == "tag1, tag2"
    
    def test_none_handling_graceful(self):
        """None値の適切な処理"""
        # TagSetとしてNoneは通常発生しないが、型安全性を確認
        context = self.context.model_copy(update={"strict_level": "warn"})
        formatter = PromptFormatter(context)
        
        # None値を含むOrderedSetの作成はできないが、
        # 空TagSetでの動作確認
        empty_tagset = OrderedSet()
        result = formatter.format_tagset(empty_tagset)
        assert result == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])