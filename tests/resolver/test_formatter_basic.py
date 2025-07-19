"""
PromptFormatter基本機能テスト

Phase1用の基本動作確認テスト
"""

import pytest
from random import Random
from ordered_set import OrderedSet

from core.resolver.formatter import PromptFormatter
from core.resolver.context import ResolverContext


class TestPromptFormatterBasic:
    """PromptFormatter基本機能のテスト"""
    
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
    
    def test_basic_tagset_formatting(self):
        """基本的なTagSetフォーマッティング"""
        tagset = OrderedSet(["masterpiece", "best quality", "detailed"])
        result = self.formatter.format_tagset(tagset)
        
        expected = "masterpiece, best quality, detailed"
        assert result == expected
    
    def test_single_tag_formatting(self):
        """単一タグのフォーマッティング"""
        tagset = OrderedSet(["masterpiece"])
        result = self.formatter.format_tagset(tagset)
        
        # 単一タグは区切り文字なし
        assert result == "masterpiece"
    
    def test_empty_tagset_formatting(self):
        """空TagSetのフォーマッティング"""
        tagset = OrderedSet()
        result = self.formatter.format_tagset(tagset)
        
        # 空TagSetは空文字列
        assert result == ""
    
    def test_order_preservation(self):
        """順序保持確認"""
        tagset = OrderedSet(["third", "first", "second"])
        result = self.formatter.format_tagset(tagset)
        
        # OrderedSetの順序が保持される
        expected = "third, first, second"
        assert result == expected
    
    def test_comma_locale(self):
        """カンマ区切り（デフォルト）"""
        context = self.context.model_copy(update={"locale": ","})
        formatter = PromptFormatter(context)
        
        tagset = OrderedSet(["tag1", "tag2", "tag3"])
        result = formatter.format_tagset(tagset)
        
        assert result == "tag1, tag2, tag3"
    
    def test_japanese_locale(self):
        """全角読点区切り"""
        context = self.context.model_copy(update={"locale": "、"})
        formatter = PromptFormatter(context)
        
        tagset = OrderedSet(["tag1", "tag2", "tag3"])
        result = formatter.format_tagset(tagset)
        
        assert result == "tag1、tag2、tag3"
    
    def test_semicolon_locale(self):
        """セミコロン区切り"""
        context = self.context.model_copy(update={"locale": ";"})
        formatter = PromptFormatter(context)
        
        tagset = OrderedSet(["tag1", "tag2", "tag3"])
        result = formatter.format_tagset(tagset)
        
        assert result == "tag1;tag2;tag3"
    
    def test_unicode_tags(self):
        """Unicode文字を含むタグの処理"""
        tagset = OrderedSet(["masterpiece", "タグ1", "🎨", "français"])
        result = self.formatter.format_tagset(tagset)
        
        expected = "masterpiece, タグ1, 🎨, français"
        assert result == expected
    
    def test_tags_with_spaces(self):
        """空白を含むタグの処理"""
        tagset = OrderedSet(["best quality", "highly detailed", "art style"])
        result = self.formatter.format_tagset(tagset)
        
        expected = "best quality, highly detailed, art style"
        assert result == expected
    
    def test_empty_string_tag(self):
        """空文字列タグの処理"""
        tagset = OrderedSet(["", "valid_tag", ""])
        result = self.formatter.format_tagset(tagset)
        
        # OrderedSetは重複除去するので""は1つだけ
        expected = ", valid_tag"
        assert result == expected


class TestPromptFormatterInternalMethods:
    """PromptFormatter内部メソッドテスト"""
    
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
    
    def test_tagset_to_list_conversion(self):
        """OrderedSet → List変換"""
        tagset = OrderedSet(["a", "b", "c"])
        result = self.formatter._tagset_to_list(tagset)
        
        assert result == ["a", "b", "c"]
        assert isinstance(result, list)
    
    def test_apply_formatting_options_passthrough(self):
        """フォーマッティングオプション（将来拡張準備完了）"""
        tags = ["tag1", "tag2", "tag3"]
        result = self.formatter._apply_formatting_options(tags)
        
        # 内容は同じだが、コピーが作成される（将来拡張対応）
        assert result == tags
        assert result is not tags  # 異なるオブジェクト（コピー）
    
    def test_validate_locale_supported(self):
        """サポート済みlocaleの検証"""
        # カンマ（カンマ+スペースに変換される）
        context = self.context.model_copy(update={"locale": ","})
        formatter = PromptFormatter(context)
        assert formatter._validate_locale() == ", "
        
        # 全角読点
        context = self.context.model_copy(update={"locale": "、"})
        formatter = PromptFormatter(context)
        assert formatter._validate_locale() == "、"
        
        # セミコロン
        context = self.context.model_copy(update={"locale": ";"})
        formatter = PromptFormatter(context)
        assert formatter._validate_locale() == ";"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])