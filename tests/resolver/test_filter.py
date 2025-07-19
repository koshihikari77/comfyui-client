"""
TagFilter包括的テストスイート

TagFilter全機能の統合テスト
PlaceholderSubstitutor, WildcardSubstitutorテスト構成を参考にした包括的なテスト
"""

import pytest
import logging
from random import Random
from ordered_set import OrderedSet
from unittest.mock import patch

from core.resolver.filter import TagFilter
from core.resolver.context import ResolverContext, PresetFile
from core.resolver.ast import TagLeaf, Text, PresetExpr, Placeholder, Wildcard
from core.resolver.exceptions import TagFilterError


class TestTagFilterBasic:
    """基本機能のテスト"""
    
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
    
    def test_single_tagleaf_processing(self):
        """単一TagLeafの処理"""
        tags = OrderedSet(["masterpiece", "best quality", "detailed"])
        ast = [TagLeaf(tags=tags)]
        
        result = self.filter.filter_ast(ast)
        
        assert result == tags
        assert isinstance(result, OrderedSet)
        assert list(result) == ["masterpiece", "best quality", "detailed"]
    
    def test_multiple_tagleaf_integration(self):
        """複数TagLeafの統合処理"""
        tags1 = OrderedSet(["masterpiece", "best quality"])
        tags2 = OrderedSet(["detailed", "HDR"])
        tags3 = OrderedSet(["masterpiece", "vibrant"])  # 重複テスト
        
        ast = [
            TagLeaf(tags=tags1),
            Text(value="separator"), 
            TagLeaf(tags=tags2),
            TagLeaf(tags=tags3)
        ]
        
        result = self.filter.filter_ast(ast)
        
        # 順序保持・重複除去確認
        expected = OrderedSet(["masterpiece", "best quality", "separator", "detailed", "HDR", "vibrant"])
        assert result == expected
    
    def test_empty_and_edge_cases(self):
        """空・エッジケースの処理"""
        # 空AST
        assert self.filter.filter_ast([]) == OrderedSet()
        
        # TagLeafなしAST
        ast_no_tagleaf = [PresetExpr(key_expr="preset")]
        assert self.filter.filter_ast(ast_no_tagleaf) == OrderedSet()
        
        # 空TagLeaf
        ast_empty_tagleaf = [TagLeaf(tags=OrderedSet())]
        assert self.filter.filter_ast(ast_empty_tagleaf) == OrderedSet()


class TestTagFilterIgnoreTags:
    """ignore_tags機能テスト"""
    
    def setup_method(self):
        """テスト用コンテキスト準備"""
        self.base_context = ResolverContext(
            presets={},
            wildcards={},
            rng=Random(42),
            strict_level="warn"
        )
    
    def test_ignore_tags_basic_filtering(self):
        """ignore_tags基本フィルタリング"""
        context = self.base_context.model_copy(update={
            "ignore_tags": {"hdr", "lowres", "bad_quality"}
        })
        filter = TagFilter(context)
        
        tags = OrderedSet(["masterpiece", "hdr", "best quality", "lowres", "detailed", "bad_quality"])
        ast = [TagLeaf(tags=tags)]
        
        result = filter.filter_ast(ast)
        
        expected = OrderedSet(["masterpiece", "best quality", "detailed"])
        assert result == expected
    
    def test_ignore_tags_normalization(self):
        """ignore_tags正規化処理"""
        context = self.base_context.model_copy(update={
            "ignore_tags": {" HDR ", "lowres", "BAD_QUALITY"}
        })
        filter = TagFilter(context)
        
        tags = OrderedSet(["masterpiece", "hdr", " lowres ", "Bad_Quality", "detailed"])
        ast = [TagLeaf(tags=tags)]
        
        result = filter.filter_ast(ast)
        
        # 正規化比較で除外される
        expected = OrderedSet(["masterpiece", "detailed"])
        assert result == expected
    
    def test_ignore_tags_multiple_tagleaf(self):
        """複数TagLeafでのignore_tags適用"""
        context = self.base_context.model_copy(update={
            "ignore_tags": {"unwanted", "bad"}
        })
        filter = TagFilter(context)
        
        tags1 = OrderedSet(["masterpiece", "unwanted", "quality"])
        tags2 = OrderedSet(["detailed", "bad", "artistic"])
        tags3 = OrderedSet(["HDR", "vibrant"])
        
        ast = [TagLeaf(tags=tags1), TagLeaf(tags=tags2), TagLeaf(tags=tags3)]
        
        result = filter.filter_ast(ast)
        
        expected = OrderedSet(["masterpiece", "quality", "detailed", "artistic", "HDR", "vibrant"])
        assert result == expected
    
    def test_ignore_tags_all_filtered(self):
        """全タグ除外時の処理"""
        context = self.base_context.model_copy(update={
            "ignore_tags": {"tag1", "tag2", "tag3"}
        })
        filter = TagFilter(context)
        
        tags = OrderedSet(["tag1", "tag2", "tag3"])
        ast = [TagLeaf(tags=tags)]
        
        result = filter.filter_ast(ast)
        
        assert result == OrderedSet()
        assert len(result) == 0


class TestTagFilterLogging:
    """ログ機能テスト"""
    
    def setup_method(self):
        """テスト用コンテキスト準備"""
        self.base_context = ResolverContext(
            presets={},
            wildcards={},
            rng=Random(42),
            ignore_tags={"hdr", "lowres"}
        )
    
    def test_warn_level_logging(self, caplog):
        """warnレベルでの警告ログ"""
        context = self.base_context.model_copy(update={"strict_level": "warn"})
        filter = TagFilter(context)
        
        tags = OrderedSet(["masterpiece", "hdr", "best quality", "lowres", "detailed"])
        ast = [TagLeaf(tags=tags)]
        
        with caplog.at_level(logging.WARNING):
            result = filter.filter_ast(ast)
        
        # 除外されたタグの警告ログ確認
        log_text = caplog.text
        assert "hdr" in log_text and "ignored by ignore_tags" in log_text
        assert "lowres" in log_text and "ignored by ignore_tags" in log_text
        
        # フィルタリング結果確認
        expected = OrderedSet(["masterpiece", "best quality", "detailed"])
        assert result == expected
    
    def test_soft_level_no_warning(self, caplog):
        """softレベルでは警告ログなし"""
        context = self.base_context.model_copy(update={"strict_level": "soft"})
        filter = TagFilter(context)
        
        tags = OrderedSet(["masterpiece", "hdr", "detailed"])
        ast = [TagLeaf(tags=tags)]
        
        with caplog.at_level(logging.WARNING):
            result = filter.filter_ast(ast)
        
        # 警告ログなし
        assert "ignored by ignore_tags" not in caplog.text
        
        # フィルタリングは実行される
        expected = OrderedSet(["masterpiece", "detailed"])
        assert result == expected
    
    def test_error_level_logging(self, caplog):
        """errorレベルでも除外は実行（ログはwarnと同様）"""
        context = self.base_context.model_copy(update={"strict_level": "error"})
        filter = TagFilter(context)
        
        tags = OrderedSet(["masterpiece", "hdr", "detailed"])
        ast = [TagLeaf(tags=tags)]
        
        with caplog.at_level(logging.WARNING):
            result = filter.filter_ast(ast)
        
        # errorレベルでも除外は実行される（情報提供として警告）
        assert "ignored by ignore_tags" in caplog.text
        expected = OrderedSet(["masterpiece", "detailed"])
        assert result == expected


class TestTagFilterErrorHandling:
    """エラーハンドリングテスト"""
    
    def setup_method(self):
        """テスト用コンテキスト準備"""
        self.base_context = ResolverContext(
            presets={},
            wildcards={},
            rng=Random(42),
            ignore_tags=set()
        )
    
    def test_error_strict_level_exception(self):
        """strict_level=errorでの例外発生"""
        context = self.base_context.model_copy(update={"strict_level": "error"})
        filter = TagFilter(context)
        
        # 強制的にエラーを発生させる
        with patch.object(OrderedSet, 'update', side_effect=RuntimeError("Test error")):
            ast = [TagLeaf(tags=OrderedSet(["tag1"]))]
            
            with pytest.raises(TagFilterError) as exc_info:
                filter.filter_ast(ast)
            
            assert "Failed to filter AST" in str(exc_info.value)
            assert "Test error" in str(exc_info.value)
    
    def test_error_warn_level_fallback(self, caplog):
        """strict_level=warnでのフォールバック処理"""
        context = self.base_context.model_copy(update={"strict_level": "warn"})
        filter = TagFilter(context)
        
        with patch.object(OrderedSet, 'update', side_effect=RuntimeError("Test error")):
            ast = [TagLeaf(tags=OrderedSet(["tag1"]))]
            
            with caplog.at_level(logging.WARNING):
                result = filter.filter_ast(ast)
            
            # 空TagSet返却
            assert result == OrderedSet()
            
            # 警告ログ確認
            assert "TagFilter error, returning empty TagSet" in caplog.text
    
    def test_error_soft_level_silent(self, caplog):
        """strict_level=softでのサイレント処理"""
        context = self.base_context.model_copy(update={"strict_level": "soft"})
        filter = TagFilter(context)
        
        with patch.object(OrderedSet, 'update', side_effect=RuntimeError("Test error")):
            ast = [TagLeaf(tags=OrderedSet(["tag1"]))]
            
            with caplog.at_level(logging.WARNING):
                result = filter.filter_ast(ast)
            
            # 空TagSet返却
            assert result == OrderedSet()
            
            # WARNING以上のTagFilterメッセージなし
            warning_messages = [rec.message for rec in caplog.records if rec.levelno >= logging.WARNING and "TagFilter error" in rec.message]
            assert len(warning_messages) == 0


class TestTagFilterPerformance:
    """性能・スケーラビリティテスト"""
    
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
    
    def test_large_tagset_performance(self):
        """大規模TagSetの処理性能"""
        # 1000タグの処理
        large_tags = OrderedSet([f"tag_{i:04d}" for i in range(1000)])
        ast = [TagLeaf(tags=large_tags)]
        
        result = self.filter.filter_ast(ast)
        
        assert len(result) == 1000
        assert result == large_tags
    
    def test_many_tagleaf_performance(self):
        """多数TagLeafの統合性能"""
        # 100個のTagLeaf（各10タグ）
        ast = []
        expected_result = OrderedSet()
        
        for i in range(100):
            tags = OrderedSet([f"group_{i}_tag_{j}" for j in range(10)])
            ast.append(TagLeaf(tags=tags))
            expected_result.update(tags)
        
        result = self.filter.filter_ast(ast)
        
        assert len(result) == 1000  # 100 * 10
        assert result == expected_result
    
    def test_unicode_and_special_characters(self):
        """Unicode・特殊文字の処理"""
        special_tags = OrderedSet([
            "タグ1", "标签2", "тег3", "🎨", "🌟",
            "tag with spaces", "tag-with-hyphens", 
            "tag_with_underscores", "UPPERCASE_TAG"
        ])
        ast = [TagLeaf(tags=special_tags)]
        
        result = self.filter.filter_ast(ast)
        
        assert result == special_tags
        assert len(result) == len(special_tags)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])