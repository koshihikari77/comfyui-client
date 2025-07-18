"""
TagFilter基本機能テスト

Phase1用の基本動作確認テスト
"""

import pytest
from random import Random
from ordered_set import OrderedSet

from core.resolver.filter import TagFilter
from core.resolver.context import ResolverContext
from core.resolver.ast import TagLeaf, Text, PresetExpr


class TestTagFilterBasic:
    """TagFilter基本機能のテスト"""
    
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
    
    def test_single_tagleaf_collection(self):
        """単一TagLeafからのタグ収集"""
        tags = OrderedSet(["masterpiece", "best quality", "detailed"])
        ast = [TagLeaf(tags=tags)]
        
        result = self.filter.filter_ast(ast)
        
        assert result == tags
        assert list(result) == ["masterpiece", "best quality", "detailed"]
    
    def test_multiple_tagleaf_integration(self):
        """複数TagLeafの統合"""
        tags1 = OrderedSet(["masterpiece", "best quality"])
        tags2 = OrderedSet(["detailed", "HDR"])
        tags3 = OrderedSet(["masterpiece", "vibrant"])  # 重複あり
        
        ast = [
            TagLeaf(tags=tags1),
            TagLeaf(tags=tags2),
            TagLeaf(tags=tags3)
        ]
        
        result = self.filter.filter_ast(ast)
        
        # 順序保持・重複除去確認
        expected = OrderedSet(["masterpiece", "best quality", "detailed", "HDR", "vibrant"])
        assert result == expected
    
    def test_mixed_ast_nodes(self):
        """混合ASTでのTagLeaf以外ノード無視"""
        tags = OrderedSet(["quality", "detailed"])
        
        ast = [
            Text(value="some text"),
            TagLeaf(tags=tags),
            PresetExpr(key_expr="style#anime"),
            Text(value="more text")
        ]
        
        result = self.filter.filter_ast(ast)
        
        # TagLeafのみが処理対象
        assert result == tags
    
    def test_empty_ast(self):
        """空ASTの処理"""
        ast = []
        result = self.filter.filter_ast(ast)
        
        assert result == OrderedSet()
        assert len(result) == 0
    
    def test_no_tagleaf_ast(self):
        """TagLeafが含まれないASTの処理"""
        ast = [
            Text(value="plain text"),
            PresetExpr(key_expr="quality#base")
        ]
        
        result = self.filter.filter_ast(ast)
        
        assert result == OrderedSet()
    
    def test_empty_tagleaf(self):
        """空のTagLeafの処理"""
        ast = [
            TagLeaf(tags=OrderedSet()),
            TagLeaf(tags=OrderedSet(["tag1", "tag2"]))
        ]
        
        result = self.filter.filter_ast(ast)
        
        assert result == OrderedSet(["tag1", "tag2"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])