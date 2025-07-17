"""
PresetEvaluator テストスイート

o3レビュー指摘事項を含む包括的なテスト
"""

import pytest
import logging
from random import Random
from ordered_set import OrderedSet

from core.resolver.preset import PresetEvaluator
from core.resolver.context import ResolverContext, PresetFile
from core.resolver.ast import PresetExpr, TagLeaf, Text
from core.resolver.exceptions import PresetNotFoundError


class TestPresetEvaluator:
    """PresetEvaluator基本機能テスト"""
    
    def setup_method(self):
        """テスト用コンテキスト準備"""
        presets = {
            "quality": PresetFile(
                version=2,
                contents={
                    "base": ["high quality", "detailed"],
                    "hdr": ["hdr", "vibrant colors"],
                    "unwanted": ["blurry", "low quality"]
                }
            ),
            "style": PresetFile(
                version=2,
                contents={
                    "anime": ["anime style", "manga"],
                    "realistic": ["photorealistic", "realistic"]
                }
            ),
            "empty": PresetFile(
                version=2,
                contents={}
            )
        }
        
        self.context = ResolverContext(
            presets=presets,
            wildcards={},
            rng=Random(42),
            strict_level="warn"
        )
        self.evaluator = PresetEvaluator(self.context)
    
    def test_simple_preset_resolution(self):
        """単純なプリセット解決"""
        ast = [PresetExpr(key_expr="quality#base")]
        result = self.evaluator.evaluate_ast(ast)
        
        assert len(result) == 1
        assert isinstance(result[0], TagLeaf)
        assert result[0].tags == OrderedSet(["high quality", "detailed"])
    
    def test_preset_without_group(self):
        """グループ指定なしプリセット（o3推奨テスト）"""
        ast = [PresetExpr(key_expr="quality")]
        result = self.evaluator.evaluate_ast(ast)
        
        assert len(result) == 1
        assert isinstance(result[0], TagLeaf)
        # 全グループのUnion
        expected = OrderedSet(["high quality", "detailed", "hdr", "vibrant colors", "blurry", "low quality"])
        assert result[0].tags == expected
    
    def test_addition_operation(self):
        """加算演算テスト"""
        ast = [PresetExpr(key_expr="quality#base+hdr")]
        result = self.evaluator.evaluate_ast(ast)
        
        assert len(result) == 1
        expected = OrderedSet(["high quality", "detailed", "hdr", "vibrant colors"])
        assert result[0].tags == expected
    
    def test_subtraction_operation(self):
        """減算演算テスト"""
        ast = [PresetExpr(key_expr="quality#base+hdr-unwanted")]
        result = self.evaluator.evaluate_ast(ast)
        
        assert len(result) == 1
        expected = OrderedSet(["high quality", "detailed", "hdr", "vibrant colors"])
        assert result[0].tags == expected
    
    def test_complex_operations_cross_preset_error(self):
        """クロスプリセット演算エラーテスト"""
        with pytest.raises(ValueError, match="Cross-preset operations are undefined"):
            ast = [PresetExpr(key_expr="quality+style#anime-quality#unwanted")]
            self.evaluator.evaluate_ast(ast)


class TestBoundaryCase:
    """o3推奨境界ケーステスト"""
    
    def setup_method(self):
        presets = {
            "test": PresetFile(
                version=2,
                contents={
                    "group": ["tag1", "tag2"],
                    "": ["empty_group_tag"]  # 空文字列グループ
                }
            )
        }
        
        self.context = ResolverContext(
            presets=presets,
            wildcards={},
            rng=Random(42),
            strict_level="warn"
        )
        self.evaluator = PresetEvaluator(self.context)
    
    def test_preset_plus_missing_group(self):
        """preset#+hdr 形式の境界ケース（o3推奨）"""
        with pytest.raises(ValueError, match="consecutive operators"):
            self.evaluator.parse_key_expr("test#+")
    
    def test_empty_group_name(self):
        """空文字列グループ名"""
        ast = [PresetExpr(key_expr="test#")]
        result = self.evaluator.evaluate_ast(ast)
        
        # グループ名が空の場合は全体扱い
        assert len(result) == 1
        expected = OrderedSet(["tag1", "tag2", "empty_group_tag"])
        assert result[0].tags == expected
    
    def test_quality_standalone(self):
        """quality単体動作テスト（o3推奨）"""
        presets = {
            "quality": PresetFile(
                version=2,
                contents={"all": ["high", "detailed"]}
            )
        }
        context = ResolverContext(
            presets=presets,
            wildcards={},
            rng=Random(),
            strict_level="warn"
        )
        evaluator = PresetEvaluator(context)
        
        ast = [PresetExpr(key_expr="quality")]
        result = evaluator.evaluate_ast(ast)
        
        assert len(result) == 1
        assert result[0].tags == OrderedSet(["high", "detailed"])
    
    def test_consecutive_operators_error(self):
        """連続演算子エラー（o3推奨明記）"""
        with pytest.raises(ValueError, match="consecutive operators"):
            self.evaluator.parse_key_expr("test#group+-other")


class TestErrorHandling:
    """エラーハンドリングテスト"""
    
    def setup_method(self):
        presets = {
            "exists": PresetFile(
                version=2,
                contents={"group": ["tag1"]}
            )
        }
        
        self.context = ResolverContext(
            presets=presets,
            wildcards={},
            rng=Random(),
            strict_level="warn"
        )
        self.evaluator = PresetEvaluator(self.context)
    
    def test_strict_level_error(self):
        """strict_level=error時の例外発生"""
        self.context.strict_level = "error"
        self.evaluator = PresetEvaluator(self.context)
        
        ast = [PresetExpr(key_expr="missing#group")]
        with pytest.raises(PresetNotFoundError, match="preset_ref=missing#group"):
            self.evaluator.evaluate_ast(ast)
    
    def test_strict_level_warn(self, caplog):
        """strict_level=warn時の警告とfallback=empty（o3推奨）"""
        self.context.strict_level = "warn"
        
        with caplog.at_level(logging.WARNING):
            ast = [PresetExpr(key_expr="missing#group")]
            result = self.evaluator.evaluate_ast(ast)
        
        # 空のTagLeafが返される
        assert len(result) == 1
        assert isinstance(result[0], TagLeaf)
        assert result[0].tags == OrderedSet()
        
        # fallback=empty ログ確認
        assert "fallback=empty" in caplog.text
        assert "strict_level=warn" in caplog.text
    
    def test_strict_level_soft(self):
        """strict_level=soft時の静寂処理"""
        self.context.strict_level = "soft"
        self.evaluator = PresetEvaluator(self.context)
        
        ast = [PresetExpr(key_expr="missing#group")]
        result = self.evaluator.evaluate_ast(ast)
        
        assert len(result) == 1
        assert result[0].tags == OrderedSet()
    
    def test_group_not_found_error_message(self):
        """グループ未発見時のエラーメッセージ（preset_ref含む）"""
        self.context.strict_level = "error"
        self.evaluator = PresetEvaluator(self.context)
        
        ast = [PresetExpr(key_expr="exists#missing")]
        with pytest.raises(PresetNotFoundError) as exc_info:
            self.evaluator.evaluate_ast(ast)
        
        assert "preset_ref=exists#missing" in str(exc_info.value)
        assert "strict_level=error" in str(exc_info.value)


class TestIgnoreGroups:
    """ignore_groups処理テスト（o3推奨：Evaluator内処理）"""
    
    def setup_method(self):
        presets = {
            "test": PresetFile(
                version=2,
                contents={
                    "normal": ["tag1", "tag2"],
                    "ignored": ["bad1", "bad2"],
                    "other": ["tag3"]
                }
            )
        }
        
        self.context = ResolverContext(
            presets=presets,
            wildcards={},
            rng=Random(),
            ignore_groups={"ignored"},
            strict_level="warn"
        )
        self.evaluator = PresetEvaluator(self.context)
    
    def test_ignore_groups_in_all_groups(self):
        """グループ指定なし時のignore_groups適用"""
        ast = [PresetExpr(key_expr="test")]
        result = self.evaluator.evaluate_ast(ast)
        
        # ignoredグループ除外される
        expected = OrderedSet(["tag1", "tag2", "tag3"])
        assert result[0].tags == expected
    
    def test_ignore_specific_group(self):
        """特定グループのignore処理"""
        ast = [PresetExpr(key_expr="test#ignored")]
        result = self.evaluator.evaluate_ast(ast)
        
        # 無視対象グループは空集合
        assert result[0].tags == OrderedSet()
    
    def test_ignore_groups_in_operations(self):
        """演算中のignore_groups適用"""
        ast = [PresetExpr(key_expr="test#normal+ignored")]
        result = self.evaluator.evaluate_ast(ast)
        
        # ignoredは空集合なので、normalのみ
        expected = OrderedSet(["tag1", "tag2"])
        assert result[0].tags == expected


class TestMixedAST:
    """混合ASTテスト"""
    
    def setup_method(self):
        presets = {
            "test": PresetFile(
                version=2,
                contents={"group": ["tag1", "tag2"]}
            )
        }
        
        self.context = ResolverContext(
            presets=presets,
            wildcards={},
            rng=Random(),
            strict_level="warn"
        )
        self.evaluator = PresetEvaluator(self.context)
    
    def test_mixed_nodes_preservation(self):
        """PresetExpr以外のノード保持確認"""
        ast = [
            Text(value="Start "),
            PresetExpr(key_expr="test#group"),
            Text(value=" End")
        ]
        
        result = self.evaluator.evaluate_ast(ast)
        
        assert len(result) == 3
        assert isinstance(result[0], Text)
        assert result[0].value == "Start "
        assert isinstance(result[1], TagLeaf)
        assert result[1].tags == OrderedSet(["tag1", "tag2"])
        assert isinstance(result[2], Text)
        assert result[2].value == " End"


class TestTokenization:
    """トークン化詳細テスト"""
    
    def setup_method(self):
        self.context = ResolverContext(
            presets={},
            wildcards={},
            rng=Random(),
            strict_level="warn"
        )
        self.evaluator = PresetEvaluator(self.context)
    
    def test_tokenize_simple(self):
        """基本トークン化"""
        result = self.evaluator.tokenize_key_expr("preset#group")
        expected = [("preset", "group", "+")]
        assert result == expected
    
    def test_tokenize_complex_cross_preset_error(self):
        """クロスプリセット演算エラーテスト"""
        with pytest.raises(ValueError, match="Cross-preset operations are undefined"):
            self.evaluator.tokenize_key_expr("a#b+c#d-e")
    
    def test_tokenize_no_group_cross_preset_error(self):
        """グループ指定なし - クロスプリセット演算エラーテスト"""
        # preset+other は preset全体 + other全体 でクロスプリセット演算
        with pytest.raises(ValueError, match="Cross-preset operations are undefined"):
            self.evaluator.tokenize_key_expr("preset+other")
    
    def test_parse_group_token_boundary(self):
        """グループトークン境界ケース"""
        # split('#', 1) テスト
        result = self.evaluator._parse_group_token("preset#group#extra")
        assert result == ("preset", "group#extra")
        
        result = self.evaluator._parse_group_token("preset#")
        assert result == ("preset", None)
        
        result = self.evaluator._parse_group_token("preset")
        assert result == ("preset", None)
    
    def test_cross_preset_operation_error(self):
        """クロスプリセット演算エラーテスト（o3推奨）"""
        with pytest.raises(ValueError, match="Cross-preset operations are undefined"):
            self.evaluator.parse_key_expr("quality+style#anime-hdr")
    
    def test_same_preset_operation_success(self):
        """同一プリセット内演算成功テスト（リグレッション）"""
        # 同一プリセット内の演算は成功すべき
        result = self.evaluator.parse_key_expr("quality#base+hdr")
        assert len(result) > 0  # 成功することを確認