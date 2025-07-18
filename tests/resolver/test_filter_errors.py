"""
TagFilter エラーハンドリングテスト

Phase3用のエラーハンドリング・strict_level対応テスト
"""

import pytest
import logging
from random import Random
from ordered_set import OrderedSet
from unittest.mock import Mock, patch

from core.resolver.filter import TagFilter
from core.resolver.context import ResolverContext
from core.resolver.ast import TagLeaf
from core.resolver.exceptions import TagFilterError


class TestTagFilterErrorHandling:
    """TagFilterエラーハンドリングのテスト"""
    
    def setup_method(self):
        """テスト用コンテキスト準備"""
        self.base_context = ResolverContext(
            presets={},
            wildcards={},
            rng=Random(42),
            ignore_tags=set()
        )
    
    def test_error_handling_strict_error(self):
        """strict_level=errorでの例外発生"""
        context = self.base_context.model_copy(update={"strict_level": "error"})
        filter = TagFilter(context)
        
        # OrderedSet.updateを強制的にエラーにする
        with patch.object(OrderedSet, 'update', side_effect=RuntimeError("Forced error")):
            ast = [TagLeaf(tags=OrderedSet(["tag1"]))]
            
            with pytest.raises(TagFilterError) as exc_info:
                filter.filter_ast(ast)
            
            assert "Failed to filter AST" in str(exc_info.value)
            assert "Forced error" in str(exc_info.value)
    
    def test_error_handling_strict_warn(self, caplog):
        """strict_level=warnでの警告ログ・空TagSet返却"""
        context = self.base_context.model_copy(update={"strict_level": "warn"})
        filter = TagFilter(context)
        
        with patch.object(OrderedSet, 'update', side_effect=RuntimeError("Forced error")):
            ast = [TagLeaf(tags=OrderedSet(["tag1"]))]
            
            with caplog.at_level(logging.WARNING):
                result = filter.filter_ast(ast)
            
            # 空TagSet返却
            assert result == OrderedSet()
            
            # 警告ログ確認
            assert "TagFilter error, returning empty TagSet" in caplog.text
            assert "Forced error" in caplog.text
    
    def test_error_handling_strict_soft(self, caplog):
        """strict_level=softでのサイレント処理"""
        context = self.base_context.model_copy(update={"strict_level": "soft"})
        filter = TagFilter(context)
        
        with patch.object(OrderedSet, 'update', side_effect=RuntimeError("Forced error")):
            ast = [TagLeaf(tags=OrderedSet(["tag1"]))]
            
            with caplog.at_level(logging.WARNING):
                result = filter.filter_ast(ast)
            
            # 空TagSet返却
            assert result == OrderedSet()
            
            # WARNING以上のログなし（ERRORログのみ）
            warning_logs = [rec for rec in caplog.records if rec.levelno >= logging.WARNING and "TagFilter error" in rec.message]
            assert len(warning_logs) == 0
    
    def test_normal_operation_no_errors(self):
        """通常動作時のエラーハンドリング非活性化"""
        context = self.base_context.model_copy(update={"strict_level": "error"})
        filter = TagFilter(context)
        
        tags = OrderedSet(["masterpiece", "best quality"])
        ast = [TagLeaf(tags=tags)]
        
        # 正常に動作することを確認
        result = filter.filter_ast(ast)
        assert result == tags
    
    def test_invalid_ast_node_graceful_handling(self):
        """不正なASTノードの優雅な処理"""
        context = self.base_context.model_copy(update={"strict_level": "warn"})
        filter = TagFilter(context)
        
        # 不正なオブジェクトを含むAST（isinstance チェックで除外される）
        invalid_node = Mock()
        invalid_node.__class__ = type("InvalidNode", (), {})
        
        ast = [
            TagLeaf(tags=OrderedSet(["valid_tag"])),
            invalid_node  # これは無視される
        ]
        
        result = filter.filter_ast(ast)
        
        # 有効なTagLeafのみ処理される
        assert result == OrderedSet(["valid_tag"])


class TestTagFilterEdgeCases:
    """TagFilterエッジケースのテスト"""
    
    def setup_method(self):
        """テスト用コンテキスト準備"""
        self.context = ResolverContext(
            presets={},
            wildcards={},
            rng=Random(42),
            ignore_tags=set(),
            strict_level="warn"
        )
        self.filter = TagFilter(self.context)
    
    def test_very_large_tagset(self):
        """大量タグセットの処理"""
        large_tags = OrderedSet([f"tag_{i}" for i in range(1000)])
        ast = [TagLeaf(tags=large_tags)]
        
        result = self.filter.filter_ast(ast)
        
        assert len(result) == 1000
        assert result == large_tags
    
    def test_unicode_tags(self):
        """Unicode文字を含むタグの処理"""
        unicode_tags = OrderedSet(["タグ1", "🎨", "test_tag", "français"])
        ast = [TagLeaf(tags=unicode_tags)]
        
        result = self.filter.filter_ast(ast)
        
        assert result == unicode_tags
    
    def test_empty_string_tags(self):
        """空文字列タグの処理"""
        tags_with_empty = OrderedSet(["", "valid_tag", ""])
        ast = [TagLeaf(tags=tags_with_empty)]
        
        result = self.filter.filter_ast(ast)
        
        # OrderedSetは重複を自動除去するので""は1つだけ
        assert "" in result
        assert "valid_tag" in result
        assert len(result) == 2
    
    def test_none_handling(self):
        """None値の適切な処理"""
        # TagLeaf自体がNoneの場合は、isinstance checkで除外される
        ast = [None, TagLeaf(tags=OrderedSet(["valid_tag"]))]
        
        # TypeErrorは発生しない（isinstanceがFalseを返すため）
        result = self.filter.filter_ast(ast)
        assert result == OrderedSet(["valid_tag"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])