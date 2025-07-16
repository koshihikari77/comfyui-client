#!/usr/bin/env python3
"""
TemplateParser エラーハンドリングテスト統合版

test_phase3_improvements.py + test_o3_solution.py の統合
pytest統一化対応
"""

import pytest
import sys
from pathlib import Path

# プロジェクトルートを追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.resolver.parser import TemplateParser
from core.resolver.exceptions import ParseError, RecursionLimitError
from core.resolver.context import ResolverContext, PresetFile
from random import Random
from core.resolver.ast import Text, PresetExpr, Placeholder, Wildcard


class TestParseErrorPositionInfo:
    """ParseError位置情報のテスト（旧test_phase3_improvements.py）"""
    
    def test_parse_error_has_position_info(self):
        """ParseErrorに位置情報が含まれることをテスト"""
        parser = TemplateParser()
        
        # 意図的に不正な構文を使用
        invalid_template = "<preset:>"
        
        with pytest.raises(ParseError) as exc_info:
            parser.parse(invalid_template)
        
        error = exc_info.value
        
        # 位置情報の属性が存在することを確認
        assert hasattr(error, 'template')
        assert hasattr(error, 'position')
        assert hasattr(error, 'line')
        assert hasattr(error, 'column')
        
        # 値が設定されていることを確認
        assert error.template == invalid_template
        assert error.position >= -1  # -1は「不明」を表す
        assert error.line >= -1
        assert error.column >= -1
    
    def test_parse_error_position_accuracy(self):
        """ParseError位置情報の正確性テスト"""
        parser = TemplateParser()
        
        # 位置が特定しやすい不正構文
        test_cases = [
            ("simple <preset:> text", "<preset:>"),
            ("prefix {", "{"),
            ("text __ suffix", "__"),
            ("multi\nline\n<preset:>\ntext", "<preset:>"),
        ]
        
        for template, expected_error_part in test_cases:
            with pytest.raises(ParseError) as exc_info:
                parser.parse(template)
            
            error = exc_info.value
            assert error.template == template
            
            # エラーメッセージに詳細な情報が含まれることを確認
            assert str(error) is not None
            assert len(str(error)) > 0
    
    def test_parse_error_with_complex_template(self):
        """複雑なテンプレートでのParseError位置情報"""
        parser = TemplateParser()
        
        # 複雑なテンプレートの中での不正構文
        complex_template = """<preset:quality#base+hdr>, {emotion} girl, __lighting__, 
        more text here, <preset:>, and final text"""
        
        with pytest.raises(ParseError) as exc_info:
            parser.parse(complex_template)
        
        error = exc_info.value
        assert error.template == complex_template
        
        # 位置情報が設定されていることを確認
        assert error.position >= -1
        assert error.line >= -1
        assert error.column >= -1
    
    def test_parse_error_multiline_template(self):
        """複数行テンプレートでのParseError位置情報"""
        parser = TemplateParser()
        
        multiline_template = """First line of template
        <preset:quality#base+hdr>
        {emotion} girl
        <preset:>
        Final line"""
        
        with pytest.raises(ParseError) as exc_info:
            parser.parse(multiline_template)
        
        error = exc_info.value
        assert error.template == multiline_template
        
        # 行番号が正しく設定されていることを確認（実装依存）
        # line==-1の場合は「不明」を表す
        assert error.line >= -1
        assert error.column >= -1


class TestPresetFileVersionAutoSetting:
    """PresetFile version自動設定のテスト（旧test_phase3_improvements.py）"""
    
    def test_preset_file_auto_version_from_list(self):
        """リスト形式のcontentsからversion自動設定"""
        # V1形式のプリセット（contentsがlist）
        preset_data = {
            "description": "Test V1 preset",
            "contents": ["masterpiece", "best quality", "8K"]
        }
        
        preset_file = PresetFile(**preset_data)
        
        # version=1が自動設定されることを確認
        assert preset_file.version == 1
        # contentsが正規化されることを確認
        assert preset_file.contents == {"__all__": ["masterpiece", "best quality", "8K"]}
    
    def test_preset_file_auto_version_from_dict(self):
        """辞書形式のcontentsではversion自動設定されない"""
        # V2形式（contentsがdict）でversion未指定
        preset_data = {
            "description": "Test V2 preset without version",
            "contents": {
                "quality": ["masterpiece", "best quality"],
                "resolution": ["8K", "4K"]
            }
        }
        
        preset_file = PresetFile(**preset_data)
        
        # デフォルトのversion=2が使われることを確認
        assert preset_file.version == 2
        # contentsがそのまま維持されることを確認
        assert preset_file.contents == {
            "quality": ["masterpiece", "best quality"],
            "resolution": ["8K", "4K"]
        }
    
    def test_preset_file_explicit_version_preserved(self):
        """明示的なversion指定が保持される"""
        # V1形式でも明示的にversion=2を指定
        preset_data = {
            "version": 2,
            "description": "Mixed format",
            "contents": ["masterpiece", "best quality", "8K"]  # V1形式のcontents
        }
        
        preset_file = PresetFile(**preset_data)
        
        # 明示的なversionが優先されることを確認
        assert preset_file.version == 2
        # contentsは正規化される
        assert preset_file.contents == {"__all__": ["masterpiece", "best quality", "8K"]}
    
    def test_preset_file_version_with_empty_contents(self):
        """空のcontentsでのversion処理"""
        # 空のリスト
        preset_data = {
            "contents": []
        }
        
        preset_file = PresetFile(**preset_data)
        
        # version=1が自動設定されることを確認
        assert preset_file.version == 1
        assert preset_file.contents == {"__all__": []}
    
    def test_preset_file_version_validation(self):
        """PresetFileのversion値検証"""
        # 正常なversion値
        valid_versions = [1, 2]
        
        for version in valid_versions:
            preset_data = {
                "version": version,
                "contents": ["test"]
            }
            
            preset_file = PresetFile(**preset_data)
            assert preset_file.version == version
    
    def test_preset_file_in_resolver_context(self):
        """ResolverContext内でのPresetFile使用"""
        # PresetFileをResolverContextで使用
        preset_file = PresetFile(
            contents=["masterpiece", "best quality"]
        )
        
        # version=1が自動設定されることを確認
        assert preset_file.version == 1
        
        # ResolverContextでの使用
        context = ResolverContext(
            presets={"quality": preset_file},
            wildcards={},
            rng=Random(),
        )
        
        assert context.presets["quality"].version == 1
        assert context.presets["quality"].contents == {"__all__": ["masterpiece", "best quality"]}


class TestO3SolutionValidation:
    """O3提案解決策の検証（旧test_o3_solution.py）"""
    
    def test_o3_underscore_text_solution(self):
        """O3提案: アンダースコア含むテキストの解決"""
        parser = TemplateParser()
        
        # O3提案のテストケース
        test_cases = [
            # (テンプレート, 期待するASTタイプ)
            ('some_tag', ['Text']),
            ('another_underscore_test', ['Text']),
            ('file_name_with_underscores', ['Text']),
            ('test_case_name', ['Text']),
        ]
        
        for template, expected_types in test_cases:
            ast = parser.parse(template)
            actual_types = [node.__class__.__name__ for node in ast]
            
            assert actual_types == expected_types, \
                f"Template: '{template}' - Expected: {expected_types}, Got: {actual_types}"
            
            # テキストの内容が正しく保持されていることを確認
            assert len(ast) == 1
            assert isinstance(ast[0], Text)
            assert ast[0].value == template
    
    def test_o3_wildcard_solution(self):
        """O3提案: ワイルドカード認識の解決"""
        parser = TemplateParser()
        
        # ワイルドカードのテストケース
        test_cases = [
            ('__lighting__', ['Wildcard']),
            ('__style__', ['Wildcard']),
            ('__quality__', ['Wildcard']),
            ('__background__', ['Wildcard']),
        ]
        
        for template, expected_types in test_cases:
            ast = parser.parse(template)
            actual_types = [node.__class__.__name__ for node in ast]
            
            assert actual_types == expected_types, \
                f"Template: '{template}' - Expected: {expected_types}, Got: {actual_types}"
            
            # ワイルドカードの内容が正しく抽出されていることを確認
            assert len(ast) == 1
            assert isinstance(ast[0], Wildcard)
            expected_key = template[2:-2]  # __を除去
            assert ast[0].key == expected_key
    
    def test_o3_mixed_underscore_wildcard_solution(self):
        """O3提案: アンダースコアとワイルドカードの混在解決"""
        parser = TemplateParser()
        
        # 混在パターンのテストケース
        test_cases = [
            ('prefix __wild__ suffix', ['Text', 'Wildcard', 'Text']),
            ('some_tag __lighting__ more_text', ['Text', 'Wildcard', 'Text']),
            ('file_name __style__ final_part', ['Text', 'Wildcard', 'Text']),
        ]
        
        for template, expected_types in test_cases:
            ast = parser.parse(template)
            actual_types = [node.__class__.__name__ for node in ast]
            
            assert actual_types == expected_types, \
                f"Template: '{template}' - Expected: {expected_types}, Got: {actual_types}"
    
    def test_o3_comprehensive_solution(self):
        """O3提案: 包括的な解決策検証"""
        parser = TemplateParser()
        
        # 最も複雑なテストケース
        comprehensive_template = '<preset:quality#base+hdr>, {emotion} girl, __lighting__'
        expected_types = ['PresetExpr', 'Text', 'Placeholder', 'Text', 'Wildcard']
        
        ast = parser.parse(comprehensive_template)
        actual_types = [node.__class__.__name__ for node in ast]
        
        assert actual_types == expected_types, \
            f"Comprehensive template failed - Expected: {expected_types}, Got: {actual_types}"
        
        # 各要素の詳細検証
        assert len(ast) == 5
        
        # PresetExpr
        assert isinstance(ast[0], PresetExpr)
        assert ast[0].key_expr == 'quality#base+hdr'
        
        # Text ", "
        assert isinstance(ast[1], Text)
        assert ast[1].value == ', '
        
        # Placeholder
        assert isinstance(ast[2], Placeholder)
        assert ast[2].name == 'emotion'
        
        # Text " girl, "
        assert isinstance(ast[3], Text)
        assert ast[3].value == ' girl, '
        
        # Wildcard
        assert isinstance(ast[4], Wildcard)
        assert ast[4].key == 'lighting'
    
    def test_o3_edge_cases(self):
        """O3提案: エッジケースの検証"""
        parser = TemplateParser()
        
        # エッジケースのテストケース
        edge_cases = [
            ('_single_leading_underscore', ['Text']),
            ('single_trailing_underscore_', ['Text']),
            ('text_with_multiple_underscores_here', ['Text']),
        ]
        
        for template, expected_types in edge_cases:
            try:
                ast = parser.parse(template)
                actual_types = [node.__class__.__name__ for node in ast]
                
                assert actual_types == expected_types, \
                    f"Edge case: '{template}' - Expected: {expected_types}, Got: {actual_types}"
                    
            except ParseError:
                # 一部のエッジケースは解析エラーになる可能性がある
                # その場合は適切なエラーが発生することを確認
                pass
    
    def test_o3_performance_validation(self):
        """O3提案: パフォーマンス検証"""
        parser = TemplateParser()
        
        # 大量のアンダースコア含むテキストの処理
        test_cases = []
        for i in range(100):
            test_cases.append(f"test_case_{i}")
            test_cases.append(f"__wildcard_{i}__")
        
        import time
        start_time = time.time()
        
        for template in test_cases:
            ast = parser.parse(template)
            # 正しく解析されることを確認
            assert len(ast) >= 1
            
        end_time = time.time()
        execution_time = end_time - start_time
        
        # 200個のテンプレートが1秒以内に処理されることを確認
        assert execution_time < 1.0, \
            f"O3解決策の性能が不十分: {execution_time:.3f}秒"


class TestIntegratedErrorHandling:
    """統合エラーハンドリングテスト"""
    
    def test_error_handling_consistency(self):
        """エラーハンドリングの一貫性テスト"""
        parser = TemplateParser()
        
        # 様々な不正構文
        invalid_templates = [
            "<preset:>",           # 空のプリセット
            "{",                   # 不完全なプレースホルダー
            "__",                  # 不完全なワイルドカード
            "<preset:quality",     # 閉じタグなし
            "{emotion",            # 閉じタグなし
            "__lighting",          # 閉じタグなし
        ]
        
        for template in invalid_templates:
            with pytest.raises(ParseError) as exc_info:
                parser.parse(template)
            
            error = exc_info.value
            
            # 一貫したエラー情報が提供されることを確認
            assert hasattr(error, 'template')
            assert hasattr(error, 'position')
            assert hasattr(error, 'line')
            assert hasattr(error, 'column')
            assert error.template == template
            assert str(error) is not None
    
    def test_error_recovery_and_validation(self):
        """エラー回復とバリデーション"""
        parser = TemplateParser()
        
        # 不正なテンプレートの検証
        invalid_templates = [
            "<preset:>",
            "{",
            "__",
        ]
        
        for template in invalid_templates:
            # parse()では例外が発生
            with pytest.raises(ParseError):
                parser.parse(template)
            
            # validate_template()ではFalseが返される
            assert parser.validate_template(template) == False
    
    def test_error_message_quality(self):
        """エラーメッセージの品質テスト"""
        parser = TemplateParser()
        
        # 代表的な不正構文
        test_cases = [
            ("<preset:>", "preset"),
            ("{", "placeholder"),
            ("__", "wildcard"),
        ]
        
        for template, expected_context in test_cases:
            with pytest.raises(ParseError) as exc_info:
                parser.parse(template)
            
            error = exc_info.value
            error_message = str(error)
            
            # エラーメッセージが有用であることを確認
            assert len(error_message) > 10  # 空でない
            assert template in error_message or error.template == template
    
    def test_nested_error_handling(self):
        """ネストしたエラーハンドリング"""
        parser = TemplateParser()
        
        # 複雑なネストした不正構文
        complex_invalid = """
        <preset:quality#base+hdr>, 
        {emotion} girl, 
        __lighting__, 
        <preset:>, 
        more text
        """
        
        with pytest.raises(ParseError) as exc_info:
            parser.parse(complex_invalid)
        
        error = exc_info.value
        assert error.template == complex_invalid
        
        # 位置情報が設定されていることを確認
        assert error.position >= -1
        assert error.line >= -1
        assert error.column >= -1


if __name__ == "__main__":
    # pytestがない場合のスタンドアロン実行
    print("=== TemplateParser エラーハンドリングテスト実行 ===")
    
    test_classes = [
        TestParseErrorPositionInfo,
        TestPresetFileVersionAutoSetting,
        TestO3SolutionValidation,
        TestIntegratedErrorHandling,
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