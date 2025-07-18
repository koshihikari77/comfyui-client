"""
TagFilter ignore_tags機能テスト

Phase2用のignore_tags適用機能テスト
"""

import pytest
import logging
from random import Random
from ordered_set import OrderedSet

from core.resolver.filter import TagFilter
from core.resolver.context import ResolverContext
from core.resolver.ast import TagLeaf


class TestTagFilterIgnoreTags:
    """ignore_tags機能のテスト"""
    
    def setup_method(self):
        """テスト用コンテキスト準備"""
        self.base_context = ResolverContext(
            presets={},
            wildcards={},
            rng=Random(42),
            strict_level="warn"
        )
    
    def test_ignore_tags_exact_match(self):
        """ignore_tags完全一致での除外"""
        context = self.base_context.model_copy(update={
            "ignore_tags": {"hdr", "lowres"}
        })
        filter = TagFilter(context)
        
        tags = OrderedSet(["masterpiece", "hdr", "best quality", "lowres", "detailed"])
        ast = [TagLeaf(tags=tags)]
        
        result = filter.filter_ast(ast)
        
        # hdr, lowresが除外される
        expected = OrderedSet(["masterpiece", "best quality", "detailed"])
        assert result == expected
    
    def test_ignore_tags_case_insensitive(self):
        """ignore_tags大文字小文字無視での除外"""
        context = self.base_context.model_copy(update={
            "ignore_tags": {"hdr", "LOWRES"}
        })
        filter = TagFilter(context)
        
        tags = OrderedSet(["masterpiece", "HDR", "lowres", "Detailed"])
        ast = [TagLeaf(tags=tags)]
        
        result = filter.filter_ast(ast)
        
        # 正規化比較でHDR→hdr, lowres→lowresで除外
        expected = OrderedSet(["masterpiece", "Detailed"])
        assert result == expected
    
    def test_ignore_tags_whitespace_normalization(self):
        """ignore_tags空白文字正規化での除外"""
        context = self.base_context.model_copy(update={
            "ignore_tags": {" hdr ", "lowres"}
        })
        filter = TagFilter(context)
        
        tags = OrderedSet(["masterpiece", "hdr", " lowres ", "detailed"])
        ast = [TagLeaf(tags=tags)]
        
        result = filter.filter_ast(ast)
        
        # 正規化比較で除外
        expected = OrderedSet(["masterpiece", "detailed"])
        assert result == expected
    
    def test_ignore_tags_no_match(self):
        """ignore_tagsに該当なしの場合"""
        context = self.base_context.model_copy(update={
            "ignore_tags": {"nonexistent", "missing"}
        })
        filter = TagFilter(context)
        
        tags = OrderedSet(["masterpiece", "best quality", "detailed"])
        ast = [TagLeaf(tags=tags)]
        
        result = filter.filter_ast(ast)
        
        # 全タグ保持
        assert result == tags
    
    def test_ignore_tags_all_filtered(self):
        """全タグが除外される場合"""
        context = self.base_context.model_copy(update={
            "ignore_tags": {"tag1", "tag2", "tag3"}
        })
        filter = TagFilter(context)
        
        tags = OrderedSet(["tag1", "tag2", "tag3"])
        ast = [TagLeaf(tags=tags)]
        
        result = filter.filter_ast(ast)
        
        # 空のOrderedSet
        assert result == OrderedSet()
        assert len(result) == 0
    
    def test_ignore_tags_partial_filtering(self):
        """一部タグのみ除外される場合"""
        context = self.base_context.model_copy(update={
            "ignore_tags": {"unwanted", "bad"}
        })
        filter = TagFilter(context)
        
        tags1 = OrderedSet(["masterpiece", "unwanted", "best quality"])
        tags2 = OrderedSet(["detailed", "bad", "vibrant"])
        
        ast = [TagLeaf(tags=tags1), TagLeaf(tags=tags2)]
        
        result = filter.filter_ast(ast)
        
        # unwanted, badが除外
        expected = OrderedSet(["masterpiece", "best quality", "detailed", "vibrant"])
        assert result == expected
    
    def test_ignore_tags_warn_logging(self, caplog):
        """warn時の警告ログ確認"""
        context = self.base_context.model_copy(update={
            "ignore_tags": {"hdr"},
            "strict_level": "warn"
        })
        filter = TagFilter(context)
        
        tags = OrderedSet(["masterpiece", "hdr", "detailed"])
        ast = [TagLeaf(tags=tags)]
        
        with caplog.at_level(logging.WARNING):
            result = filter.filter_ast(ast)
        
        # 警告ログ確認
        assert "ignored by ignore_tags" in caplog.text
        assert "hdr" in caplog.text
        
        # 除外は実行される
        expected = OrderedSet(["masterpiece", "detailed"])
        assert result == expected
    
    def test_ignore_tags_soft_no_logging(self, caplog):
        """softレベル時はログ出力なし"""
        context = self.base_context.model_copy(update={
            "ignore_tags": {"hdr"},
            "strict_level": "soft"
        })
        filter = TagFilter(context)
        
        tags = OrderedSet(["masterpiece", "hdr", "detailed"])
        ast = [TagLeaf(tags=tags)]
        
        with caplog.at_level(logging.WARNING):
            result = filter.filter_ast(ast)
        
        # 警告ログなし
        assert "ignored by ignore_tags" not in caplog.text
        
        # 除外は実行される
        expected = OrderedSet(["masterpiece", "detailed"])
        assert result == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])