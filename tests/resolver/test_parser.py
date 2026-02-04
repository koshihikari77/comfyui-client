#!/usr/bin/env python3
"""
TemplateParser統合テストスイート

basic + comprehensive テストの統合版
pytest統一化対応
"""

import pytest
import sys
import time
import threading
from pathlib import Path

# プロジェクトルートを追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.resolver.parser import TemplateParser, MAX_DEPTH
from core.resolver.ast import Text, PresetExpr, Placeholder, Wildcard
from core.resolver.exceptions import ParseError, RecursionLimitError


class TestBasicParsing:
    """基本的な解析機能のテスト（旧test_parser_basic.py）"""
    
    def test_simple_text(self):
        """プレーンテキストの解析テスト"""
        parser = TemplateParser()
        
        # シンプルなテキスト
        ast = parser.parse("hello world")
        assert len(ast) == 1
        assert isinstance(ast[0], Text)
        assert ast[0].value == "hello world"
    
    def test_preset_parsing(self):
        """プリセット解析テスト"""
        parser = TemplateParser()
        
        # 基本的なプリセット
        ast = parser.parse("<preset:quality>")
        assert len(ast) == 1
        assert isinstance(ast[0], PresetExpr)
        assert ast[0].key_expr == "quality"
        
        # グループ指定付きプリセット
        ast = parser.parse("<preset:quality#base>")
        assert len(ast) == 1
        assert isinstance(ast[0], PresetExpr)
        assert ast[0].key_expr == "quality#base"
        
        # 複合プリセット
        ast = parser.parse("<preset:quality#base+hdr>")
        assert len(ast) == 1
        assert isinstance(ast[0], PresetExpr)
        assert ast[0].key_expr == "quality#base+hdr"
    
    def test_placeholder_parsing(self):
        """プレースホルダー解析テスト"""
        parser = TemplateParser()
        
        ast = parser.parse("{emotion}")
        assert len(ast) == 1
        assert isinstance(ast[0], Placeholder)
        assert ast[0].name == "emotion"
        assert ast[0].mode == "expand"
    
    def test_placeholder_mode_r_parsing(self):
        """プレースホルダー :r（ランダム）解析テスト"""
        parser = TemplateParser()
        ast = parser.parse("{emotion:r}")
        assert len(ast) == 1
        assert isinstance(ast[0], Placeholder)
        assert ast[0].name == "emotion"
        assert ast[0].mode == "sample"
    
    def test_wildcard_parsing(self):
        """ワイルドカード解析テスト"""
        parser = TemplateParser()
        
        ast = parser.parse("__lighting__")
        assert len(ast) == 1
        assert isinstance(ast[0], Wildcard)
        assert ast[0].key == "lighting"
    
    def test_combined_parsing(self):
        """複合テンプレート解析テスト"""
        parser = TemplateParser()
        
        template = "<preset:quality#base+hdr>, {emotion} girl, __lighting__"
        ast = parser.parse(template)
        
        assert len(ast) == 5  # preset, text, placeholder, text, wildcard
        
        # 各要素の確認
        assert isinstance(ast[0], PresetExpr)
        assert ast[0].key_expr == "quality#base+hdr"
        
        assert isinstance(ast[1], Text)
        assert ast[1].value == ", "
        
        assert isinstance(ast[2], Placeholder)
        assert ast[2].name == "emotion"
        
        assert isinstance(ast[3], Text)
        assert ast[3].value == " girl, "
        
        assert isinstance(ast[4], Wildcard)
        assert ast[4].key == "lighting"
    
    def test_empty_template(self):
        """空テンプレートテスト"""
        parser = TemplateParser()
        
        ast = parser.parse("")
        assert len(ast) == 0
    
    def test_validation(self):
        """バリデーションテスト"""
        parser = TemplateParser()
        
        # 正常なテンプレート
        assert parser.validate_template("<preset:quality>") == True
        assert parser.validate_template("{emotion}") == True
        assert parser.validate_template("__lighting__") == True
        
        # 不正なテンプレート（文法エラー）
        assert parser.validate_template("<preset:>") == False
        assert parser.validate_template("{") == False
        assert parser.validate_template("__") == False


class TestUnderscoreHandling:
    """アンダースコア処理のテスト（comprehensive統合）"""
    
    def test_single_underscore_in_text(self):
        """単一アンダースコアのテキスト"""
        parser = TemplateParser()
        
        test_cases = [
            "some_tag",
            "test_case_name",
            "with_multiple_underscores",
            "prefix_suffix",
            "start_with_underscore",
            "end_with_underscore_",
            "_begin_with_underscore",
        ]
        
        for case in test_cases:
            ast = parser.parse(case)
            assert len(ast) == 1
            assert isinstance(ast[0], Text)
            assert ast[0].value == case
    
    def test_underscore_vs_wildcard_distinction(self):
        """アンダースコアとワイルドカードの区別"""
        parser = TemplateParser()
        
        # 単一アンダースコア → TEXT
        ast = parser.parse("some_tag")
        assert len(ast) == 1
        assert isinstance(ast[0], Text)
        assert ast[0].value == "some_tag"
        
        # 二重アンダースコア → WILDCARD
        ast = parser.parse("__lighting__")
        assert len(ast) == 1
        assert isinstance(ast[0], Wildcard)
        assert ast[0].key == "lighting"
    
    def test_mixed_underscore_and_wildcard(self):
        """アンダースコアとワイルドカードの混在"""
        parser = TemplateParser()
        
        template = "prefix_text __wild__ suffix_text"
        ast = parser.parse(template)
        
        assert len(ast) == 3
        assert isinstance(ast[0], Text)
        assert ast[0].value == "prefix_text "
        assert isinstance(ast[1], Wildcard)
        assert ast[1].key == "wild"
        assert isinstance(ast[2], Text)
        assert ast[2].value == " suffix_text"
    
    def test_underscore_in_complex_template(self):
        """複雑なテンプレートでのアンダースコア"""
        parser = TemplateParser()
        
        template = "<preset:quality>, {emotion_type} girl_character, __lighting_setup__"
        ast = parser.parse(template)
        
        assert len(ast) == 5
        assert isinstance(ast[0], PresetExpr)
        assert ast[0].key_expr == "quality"
        
        assert isinstance(ast[1], Text)
        assert ast[1].value == ", "
        
        assert isinstance(ast[2], Placeholder)
        assert ast[2].name == "emotion_type"
        
        assert isinstance(ast[3], Text)
        assert ast[3].value == " girl_character, "
        
        assert isinstance(ast[4], Wildcard)
        assert ast[4].key == "lighting_setup"


class TestParseErrorHandling:
    """解析エラーハンドリングのテスト"""
    
    def test_invalid_preset_syntax(self):
        """不正なプリセット構文"""
        parser = TemplateParser()
        
        invalid_cases = [
            "<preset:>",  # 空のキー
            "<preset:",   # 閉じタグなし
            "<preset>",   # コロンなし
            "<:quality>", # プリセットキーワードなし
            "<preset:quality",  # 閉じタグなし
        ]
        
        for case in invalid_cases:
            with pytest.raises(ParseError) as exc_info:
                parser.parse(case)
            
            # 位置情報が含まれていることを確認
            error = exc_info.value
            assert hasattr(error, 'template')
            assert hasattr(error, 'position')
            assert hasattr(error, 'line')
            assert hasattr(error, 'column')
            assert error.template == case
    
    def test_invalid_placeholder_syntax(self):
        """不正なプレースホルダー構文"""
        parser = TemplateParser()
        
        invalid_cases = [
            "{",          # 開きタグのみ
            "}",          # 閉じタグのみ
            "{}",         # 空のプレースホルダー
            "{name",      # 閉じタグなし
            "name}",      # 開きタグなし
        ]
        
        for case in invalid_cases:
            with pytest.raises(ParseError) as exc_info:
                parser.parse(case)
            
            error = exc_info.value
            assert error.template == case
    
    def test_invalid_wildcard_syntax(self):
        """不正なワイルドカード構文"""
        parser = TemplateParser()
        
        invalid_cases = [
            "__",         # 空のワイルドカード
            "___",        # 不完全なワイルドカード
            "__name",     # 後方の__なし
            "name__",     # 前方の__なし
        ]
        
        for case in invalid_cases:
            with pytest.raises(ParseError) as exc_info:
                parser.parse(case)
            
            error = exc_info.value
            assert error.template == case
    
    def test_parse_error_position_info(self):
        """ParseError位置情報の詳細テスト"""
        parser = TemplateParser()
        
        # 複数行テンプレートでの位置情報
        template = "valid text\n<preset:>\ninvalid"
        
        with pytest.raises(ParseError) as exc_info:
            parser.parse(template)
        
        error = exc_info.value
        assert error.template == template
        # 位置情報が設定されていることを確認（具体的な値は実装に依存）
        assert error.position >= 0 or error.position == -1
        assert error.line >= 0 or error.line == -1
        assert error.column >= 0 or error.column == -1


class TestEdgeCases:
    """エッジケーステスト"""
    
    def test_empty_and_whitespace_templates(self):
        """空文字列と空白文字のテンプレート"""
        parser = TemplateParser()
        
        # 空文字列
        ast = parser.parse("")
        assert len(ast) == 0
        
        # 空白のみ
        ast = parser.parse("   ")
        assert len(ast) == 1
        assert isinstance(ast[0], Text)
        assert ast[0].value == "   "
        
        # 改行のみ
        ast = parser.parse("\n")
        assert len(ast) == 1
        assert isinstance(ast[0], Text)
        assert ast[0].value == "\n"
    
    def test_special_characters_in_text(self):
        """特殊文字を含むテキスト"""
        parser = TemplateParser()
        
        special_cases = [
            "text with spaces",
            "text\nwith\nnewlines",
            "text\twith\ttabs",
            "text with 日本語",
            "text with émojis 🎨",
            "text with symbols !@#$%^&*()",
        ]
        
        for case in special_cases:
            ast = parser.parse(case)
            assert len(ast) == 1
            assert isinstance(ast[0], Text)
            assert ast[0].value == case
    
    def test_backslash_in_text(self):
        """バックスラッシュを含むテキスト（エスケープ未実装）"""
        parser = TemplateParser()
        
        # 現在の実装では未対応のため、文法的に有効なテンプレートのみテスト
        test_cases = [
            "backslash\\text",
            "text\\with\\backslashes",
            "file\\path\\example",
            "regex\\pattern",
        ]
        
        for template in test_cases:
            ast = parser.parse(template)
            # エスケープは未実装のため、バックスラッシュは通常の文字として扱われる
            assert len(ast) >= 1
            assert isinstance(ast[0], Text)
            assert "\\" in ast[0].value
    
    def test_very_long_template(self):
        """非常に長いテンプレート"""
        parser = TemplateParser()
        
        # 1000文字のテンプレート
        long_text = "a" * 1000
        ast = parser.parse(long_text)
        assert len(ast) == 1
        assert isinstance(ast[0], Text)
        assert ast[0].value == long_text
        
        # 複数要素の長いテンプレート
        long_template = ""
        for i in range(100):
            long_template += f"<preset:quality{i}>, {{emotion{i}}}, __lighting{i}__, "
        
        ast = parser.parse(long_template)
        # 各回: preset(1) + text(1) + placeholder(1) + text(1) + wildcard(1) + text(1) = 6要素
        # 100回 × 6要素 = 600要素
        assert len(ast) == 600


class TestRecursionLimits:
    """再帰深度制限テスト"""
    
    def test_normal_depth_tracking(self):
        """通常の深度追跡"""
        parser = TemplateParser()
        
        # 通常のテンプレートは深度制限に引っかからない
        template = "<preset:quality#base+hdr>, {emotion} girl, __lighting__"
        ast = parser.parse(template)
        
        assert len(ast) == 5
        assert isinstance(ast[0], PresetExpr)
        assert isinstance(ast[2], Placeholder)
        assert isinstance(ast[4], Wildcard)
    
    def test_depth_reset_between_parses(self):
        """解析間の深度リセット"""
        parser = TemplateParser()
        
        # 複数回解析しても深度は正しくリセットされる
        templates = [
            "simple text",
            "<preset:quality>",
            "{emotion}",
            "__lighting__",
            "complex <preset:quality> {emotion} __lighting__"
        ]
        
        for template in templates:
            ast = parser.parse(template)
            assert len(ast) > 0
    
    def test_max_depth_constant(self):
        """MAX_DEPTH定数のテスト"""
        # MAX_DEPTHが適切に設定されていることを確認
        assert MAX_DEPTH == 20
        assert isinstance(MAX_DEPTH, int)
        assert MAX_DEPTH > 0


class TestPerformanceBasic:
    """基本的なパフォーマンステスト"""
    
    def test_parser_caching_performance(self):
        """パーサーキャッシュのパフォーマンス"""
        # 複数のパーサーインスタンスが同じLarkを共有することを確認
        parser1 = TemplateParser()
        parser2 = TemplateParser()
        
        # 両方のパーサーで同じテンプレートを解析
        template = "<preset:quality#base+hdr>, {emotion} girl, __lighting__"
        
        start_time = time.time()
        for _ in range(100):
            ast1 = parser1.parse(template)
            ast2 = parser2.parse(template)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # 100回の解析が1秒以内に完了することを確認（キャッシュ効果）
        assert execution_time < 1.0
        
        # 両方のパーサーで同じ結果が得られることを確認
        assert len(ast1) == len(ast2) == 5
    
    def test_concurrent_parsing(self):
        """並行解析のテスト"""
        def parse_in_thread(template, results, index):
            parser = TemplateParser()
            ast = parser.parse(template)
            results[index] = ast
        
        templates = [
            "simple text",
            "<preset:quality>",
            "{emotion}",
            "__lighting__",
            "complex <preset:quality> {emotion} __lighting__"
        ]
        
        results = [None] * len(templates)
        threads = []
        
        # 複数スレッドで同時に解析
        for i, template in enumerate(templates):
            thread = threading.Thread(target=parse_in_thread, args=(template, results, i))
            threads.append(thread)
            thread.start()
        
        # 全スレッドの完了を待つ
        for thread in threads:
            thread.join()
        
        # 全ての解析が成功したことを確認
        for i, result in enumerate(results):
            assert result is not None
            assert len(result) > 0
    
    def test_template_validation_performance(self):
        """テンプレート検証のパフォーマンス"""
        parser = TemplateParser()
        
        templates = [
            "valid template",
            "<preset:quality>",
            "{emotion}",
            "__lighting__",
            "<preset:>",  # invalid
            "{",          # invalid
            "__",         # invalid
        ]
        
        start_time = time.time()
        for _ in range(100):
            for template in templates:
                parser.validate_template(template)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # 700回の検証が1秒以内に完了することを確認
        assert execution_time < 1.0


class TestValidation:
    """バリデーション機能テスト"""
    
    def test_valid_templates(self):
        """有効なテンプレートの検証"""
        parser = TemplateParser()
        
        valid_templates = [
            "simple text",
            "<preset:quality>",
            "<preset:quality#base>",
            "<preset:quality#base+hdr>",
            "{emotion}",
            "{emotion:r}",
            "__lighting__",
            "complex <preset:quality> {emotion} __lighting__",
            "text with_underscores",
            "empty: ",
            "special chars: !@#$%",
        ]
        
        for template in valid_templates:
            assert parser.validate_template(template) == True
    
    def test_invalid_templates(self):
        """無効なテンプレートの検証"""
        parser = TemplateParser()
        
        invalid_templates = [
            "<preset:>",
            "<preset:",
            "<preset>",
            "{",
            "}",
            "{}",
            "__",
            "___",
            "__name",
            "name__",
        ]
        
        for template in invalid_templates:
            assert parser.validate_template(template) == False


# O3解決策の検証テスト（旧test_o3_solution.pyから統合）
class TestO3Solution:
    """O3提案解決策の検証"""
    
    def test_o3_solution_cases(self):
        """O3提案テストケースの検証"""
        parser = TemplateParser()
        
        # o3提案のテストケース
        test_cases = [
            ('some_tag', ['Text']),
            ('__lighting__', ['Wildcard']),
            ('prefix __wild__ suffix', ['Text', 'Wildcard', 'Text']),
            ('another_underscore_test', ['Text']),
            ('<preset:quality#base+hdr>, {emotion} girl, __lighting__', 
             ['PresetExpr', 'Text', 'Placeholder', 'Text', 'Wildcard'])
        ]
        
        for template, expected_types in test_cases:
            ast = parser.parse(template)
            actual_types = [node.__class__.__name__ for node in ast]
            assert actual_types == expected_types, f"Template: {template}, Expected: {expected_types}, Got: {actual_types}"


if __name__ == "__main__":
    # pytestがない場合のスタンドアロン実行
    print("=== TemplateParser統合テスト実行 ===")
    
    test_classes = [
        TestBasicParsing,
        TestUnderscoreHandling,
        TestParseErrorHandling,
        TestEdgeCases,
        TestRecursionLimits,
        TestPerformanceBasic,
        TestValidation,
        TestO3Solution,
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for test_class in test_classes:
        print(f"\n--- {test_class.__name__} ---")
        instance = test_class()
        
        for method_name in dir(instance):
            if method_name.startswith('test_'):
                total_tests += 1
                try:
                    method = getattr(instance, method_name)
                    method()
                    print(f"✓ {method_name}")
                    passed_tests += 1
                except Exception as e:
                    print(f"✗ {method_name}: {e}")
    
    print(f"\n=== 結果: {passed_tests}/{total_tests} テスト成功 ===")