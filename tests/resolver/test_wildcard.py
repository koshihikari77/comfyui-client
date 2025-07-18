"""
WildcardSubstitutor テストスイート

WildcardSubstitutor実装のテスト
PlaceholderSubstitutorのテストパターンを参考にした包括的なテスト
"""

import pytest
import logging
from random import Random

from core.resolver.wildcard import WildcardSubstitutor
from core.resolver.context import ResolverContext, PresetFile
from core.resolver.ast import Wildcard, Text, TagLeaf
from core.resolver.exceptions import WildcardError, RecursionLimitError


class TestWildcardSubstitutorBasic:
    """基本機能のテスト"""
    
    def setup_method(self):
        """テスト用コンテキスト準備"""
        self.context = ResolverContext(
            presets={},
            wildcards={
                "hair_color": ["blonde", "brunette", "red"],
                "emotion": ["happy", "sad", "angry"],
                "single": ["only_one"],
                "empty": []
            },
            rng=Random(42),  # 決定論的テスト
            strict_level="warn"
        )
        self.substitutor = WildcardSubstitutor(self.context)
    
    def test_single_wildcard_substitution(self):
        """単一ワイルドカードの置換"""
        ast = [Text(value="1girl, "), Wildcard(key="hair_color"), Text(value=" hair")]
        result = self.substitutor.substitute_ast(ast)
        
        assert len(result) == 3
        assert isinstance(result[0], Text)
        assert result[0].value == "1girl, "
        assert isinstance(result[1], Text)
        assert result[1].value in ["blonde", "brunette", "red"]
        assert isinstance(result[2], Text)
        assert result[2].value == " hair"
    
    def test_multiple_wildcards_substitution(self):
        """複数ワイルドカードの置換"""
        ast = [
            Text(value="1girl, "), 
            Wildcard(key="hair_color"), 
            Text(value=" hair, "), 
            Wildcard(key="emotion")
        ]
        result = self.substitutor.substitute_ast(ast)
        
        assert len(result) == 4
        assert isinstance(result[0], Text)
        assert result[0].value == "1girl, "
        assert isinstance(result[1], Text)
        assert result[1].value in ["blonde", "brunette", "red"]
        assert isinstance(result[2], Text)
        assert result[2].value == " hair, "
        assert isinstance(result[3], Text)
        assert result[3].value in ["happy", "sad", "angry"]
    
    def test_no_wildcards(self):
        """ワイルドカードが無い場合"""
        ast = [Text(value="simple text")]
        result = self.substitutor.substitute_ast(ast)
        
        assert len(result) == 1
        assert isinstance(result[0], Text)
        assert result[0].value == "simple text"
    
    def test_single_candidate_wildcard(self):
        """単一候補のワイルドカード"""
        ast = [Wildcard(key="single")]
        result = self.substitutor.substitute_ast(ast)
        
        assert len(result) == 1
        assert isinstance(result[0], Text)
        assert result[0].value == "only_one"
    
    def test_rng_deterministic(self):
        """乱数の決定論的動作確認"""
        # 同じシードで複数回実行して同じ結果が得られることを確認
        ast = [Wildcard(key="hair_color")]
        
        # 1回目
        result1 = self.substitutor.substitute_ast(ast)
        first_choice = result1[0].value
        
        # 2回目（同じシード）
        self.context = self.context.with_seed(42)
        self.substitutor = WildcardSubstitutor(self.context)
        result2 = self.substitutor.substitute_ast(ast)
        second_choice = result2[0].value
        
        assert first_choice == second_choice


class TestWildcardSubstitutorErrorHandling:
    """エラーハンドリングのテスト"""
    
    def setup_method(self):
        """テスト用コンテキスト準備"""
        self.base_context = ResolverContext(
            presets={},
            wildcards={
                "valid": ["option1", "option2"],
                "empty": []
            },
            rng=Random(42)
        )
    
    def test_undefined_wildcard_error(self):
        """未定義ワイルドカード（errorレベル）"""
        context = self.base_context.model_copy(update={"strict_level": "error"})
        substitutor = WildcardSubstitutor(context)
        
        ast = [Wildcard(key="undefined")]
        
        with pytest.raises(WildcardError) as exc_info:
            substitutor.substitute_ast(ast)
        
        assert "not defined" in str(exc_info.value)
        assert exc_info.value.wildcard_key == "undefined"
    
    def test_undefined_wildcard_warn(self, caplog):
        """未定義ワイルドカード（warnレベル）"""
        context = self.base_context.model_copy(update={"strict_level": "warn"})
        substitutor = WildcardSubstitutor(context)
        
        ast = [Wildcard(key="undefined")]
        
        with caplog.at_level(logging.WARNING):
            result = substitutor.substitute_ast(ast)
        
        # 警告ログが出力されていることを確認
        assert "not defined" in caplog.text
        
        # フォールバック処理が動作することを確認
        assert len(result) == 1
        assert isinstance(result[0], Text)
        assert result[0].value == "__undefined__"
    
    def test_undefined_wildcard_soft(self):
        """未定義ワイルドカード（softレベル）"""
        context = self.base_context.model_copy(update={"strict_level": "soft"})
        substitutor = WildcardSubstitutor(context)
        
        ast = [Wildcard(key="undefined")]
        result = substitutor.substitute_ast(ast)
        
        # 静かにフォールバック処理が動作することを確認
        assert len(result) == 1
        assert isinstance(result[0], Text)
        assert result[0].value == "__undefined__"
    
    def test_empty_wildcard_candidates_error(self):
        """空のワイルドカード候補（errorレベル）"""
        context = self.base_context.model_copy(update={"strict_level": "error"})
        substitutor = WildcardSubstitutor(context)
        
        ast = [Wildcard(key="empty")]
        
        with pytest.raises(WildcardError) as exc_info:
            substitutor.substitute_ast(ast)
        
        assert "no candidates" in str(exc_info.value)
        assert exc_info.value.wildcard_key == "empty"
    
    def test_empty_wildcard_candidates_warn(self, caplog):
        """空のワイルドカード候補（warnレベル）"""
        context = self.base_context.model_copy(update={"strict_level": "warn"})
        substitutor = WildcardSubstitutor(context)
        
        ast = [Wildcard(key="empty")]
        
        with caplog.at_level(logging.WARNING):
            result = substitutor.substitute_ast(ast)
        
        # 警告ログが出力されていることを確認
        assert "no candidates" in caplog.text
        
        # 空文字列で置換されることを確認
        assert len(result) == 1
        assert isinstance(result[0], Text)
        assert result[0].value == ""
    
    def test_empty_wildcard_candidates_soft(self):
        """空のワイルドカード候補（softレベル）"""
        context = self.base_context.model_copy(update={"strict_level": "soft"})
        substitutor = WildcardSubstitutor(context)
        
        ast = [Wildcard(key="empty")]
        result = substitutor.substitute_ast(ast)
        
        # 静かに空文字列で置換されることを確認
        assert len(result) == 1
        assert isinstance(result[0], Text)
        assert result[0].value == ""


class TestWildcardSubstitutorEdgeCases:
    """エッジケースのテスト"""
    
    def setup_method(self):
        """テスト用コンテキスト準備"""
        self.context = ResolverContext(
            presets={},
            wildcards={
                "test": ["value1", "value2", "value3"]
            },
            rng=Random(42),
            strict_level="warn"
        )
        self.substitutor = WildcardSubstitutor(self.context)
    
    def test_empty_ast(self):
        """空のAST"""
        ast = []
        result = self.substitutor.substitute_ast(ast)
        
        assert result == []
    
    def test_mixed_nodes_preservation(self):
        """混在ノードの保持確認"""
        from core.resolver.ast import PresetExpr, Placeholder, TagLeaf
        from ordered_set import OrderedSet
        
        ast = [
            Text(value="start "),
            PresetExpr(key_expr="quality#base"),
            Text(value=" middle "),
            Wildcard(key="test"),
            Text(value=" end "),
            Placeholder(name="emotion"),
            TagLeaf(tags=OrderedSet(["tag1", "tag2"]))
        ]
        
        result = self.substitutor.substitute_ast(ast)
        
        # Wildcard以外のノードは変更されないことを確認
        assert len(result) == 7
        assert isinstance(result[0], Text)
        assert result[0].value == "start "
        assert isinstance(result[1], PresetExpr)
        assert result[1].key_expr == "quality#base"
        assert isinstance(result[2], Text)
        assert result[2].value == " middle "
        assert isinstance(result[3], Text)  # Wildcardが置換される
        assert result[3].value in ["value1", "value2", "value3"]
        assert isinstance(result[4], Text)
        assert result[4].value == " end "
        assert isinstance(result[5], Placeholder)
        assert result[5].name == "emotion"
        assert isinstance(result[6], TagLeaf)
        assert list(result[6].tags) == ["tag1", "tag2"]


class TestWildcardSubstitutorReparse:
    """再パース機能テスト（WildcardSubstitutor版）"""
    
    def setup_method(self):
        """テスト用コンテキスト準備"""
        presets = {
            "quality": PresetFile(
                version=2,
                contents={
                    "base": ["masterpiece", "best quality"],
                    "hdr": ["HDR", "vibrant colors"]
                }
            )
        }
        
        self.context = ResolverContext(
            presets=presets,
            wildcards={
                "style_with_preset": ["<preset:quality#base>", "photorealistic"],
                "style_with_placeholder": ["{emotion}, detailed", "simple style"],
                "nested_wildcard": ["__hair_color__, style", "plain"],
                "hair_color": ["blonde", "brunette", "red"]
            },
            rng=Random(42),
            placeholders={
                "emotion": ["happy", "sad", "excited"]
            },
            strict_level="warn"
        )
    
    def test_preset_reparse(self):
        """プリセット再パース"""
        substitutor = WildcardSubstitutor(self.context)
        ast = [Text(value="1girl, "), Wildcard(key="style_with_preset")]
        
        result = substitutor.substitute_ast(ast)
        
        # 再パースによりTagLeafが生成される
        assert len(result) >= 2
        assert isinstance(result[0], Text)
        assert result[0].value == "1girl, "
        # プリセット展開の結果はTagLeafまたはText
        assert isinstance(result[1], (TagLeaf, Text))
    
    def test_placeholder_reparse(self):
        """プレースホルダー再パース"""
        substitutor = WildcardSubstitutor(self.context)
        ast = [Wildcard(key="style_with_placeholder")]
        
        result = substitutor.substitute_ast(ast)
        
        # プレースホルダー展開の結果を確認
        assert len(result) >= 1
        # 結果がTextまたは複数ノードであることを確認
        if len(result) == 1:
            assert isinstance(result[0], Text)
            # プレースホルダーが展開されていることを確認
            assert any(emotion in result[0].value for emotion in ["happy", "sad", "excited"]) or "simple style" in result[0].value
    
    def test_wildcard_reparse(self):
        """ワイルドカード再パース"""
        substitutor = WildcardSubstitutor(self.context)
        ast = [Wildcard(key="nested_wildcard")]
        
        result = substitutor.substitute_ast(ast)
        
        # ネストしたワイルドカードが展開されることを確認
        assert len(result) >= 1
        if isinstance(result[0], Text):
            # hair_colorが展開されているか、"plain"が選択されている
            assert any(color in result[0].value for color in ["blonde", "brunette", "red"]) or "plain" in result[0].value
    
    def test_no_reparse_needed(self):
        """再パース不要な場合"""
        context = self.context.model_copy(update={
            "wildcards": {"simple": ["just text", "no template syntax"]}
        })
        substitutor = WildcardSubstitutor(context)
        
        ast = [Wildcard(key="simple")]
        result = substitutor.substitute_ast(ast)
        
        # 単純なText置換のみ
        assert len(result) == 1
        assert isinstance(result[0], Text)
        assert result[0].value in ["just text", "no template syntax"]
    
    def test_reparse_needs_detection(self):
        """再パース判定テスト"""
        substitutor = WildcardSubstitutor(self.context)
        
        # テスト用の内部メソッド
        assert substitutor._needs_reparse("<preset:quality>") == True
        assert substitutor._needs_reparse("{placeholder}") == True
        assert substitutor._needs_reparse("__wildcard__") == True
        assert substitutor._needs_reparse("normal text") == False
        assert substitutor._needs_reparse("text with _ underscore") == False
        assert substitutor._needs_reparse("text with < bracket") == False
    
    def test_reparse_error_handling(self, caplog):
        """再パースエラーハンドリング"""
        # 存在しないプリセットを含む候補
        context = self.context.model_copy(update={
            "wildcards": {"invalid": ["<preset:nonexistent>"]}
        })
        
        substitutor = WildcardSubstitutor(context)
        ast = [Wildcard(key="invalid")]
        
        with caplog.at_level(logging.WARNING):
            result = substitutor.substitute_ast(ast)
        
        # PresetEvaluatorがwarnレベルで空のTagLeafを返すため
        assert len(result) == 1
        assert isinstance(result[0], TagLeaf)
        assert len(result[0].tags) == 0  # 空のTagSet
        
        # PresetNotFoundの警告ログが出力されているかチェック
        assert "PresetNotFound" in caplog.text
    
    def test_reparse_depth_management(self):
        """再パース深度管理テスト"""
        # 深度カウンタのリセット機能テスト
        context = self.context
        context.reset_reparse_depth()
        assert context.reparse_depth == 0
        
        # 再パース実行時の深度増加確認
        substitutor = WildcardSubstitutor(context)
        ast = [Wildcard(key="style_with_preset")]  # <preset:quality#base>を含む
        
        result = substitutor.substitute_ast(ast)
        
        # 実行後は深度がリセットされていること
        assert context.reparse_depth == 0
    
    def test_parser_cache_effectiveness(self):
        """Parserキャッシュ効果テスト"""
        substitutor = WildcardSubstitutor(self.context)
        
        # 同じ文字列を複数回パースさせる（手動でキャッシュテスト）
        choice = "<preset:quality#base>"
        
        # 1回目：キャッシュミス
        result1 = substitutor._parse_with_cache(choice)
        assert choice in substitutor._parse_cache
        
        # 2回目：キャッシュヒット
        result2 = substitutor._parse_with_cache(choice)
        
        # 独立したオブジェクトが返されることを確認
        assert result1 is not result2  # 異なるオブジェクト
        assert len(result1) == len(result2)  # 内容は同じ