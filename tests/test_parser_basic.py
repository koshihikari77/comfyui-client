"""
TemplateParser基本機能テスト
"""

import sys
sys.path.append('.')

from core.resolver.parser import TemplateParser
from core.resolver.ast import Text, PresetExpr, Placeholder, Wildcard
from core.resolver.exceptions import ParseError, RecursionLimitError

def test_simple_text():
    """プレーンテキストの解析テスト"""
    parser = TemplateParser()
    
    # シンプルなテキスト
    ast = parser.parse("hello world")
    assert len(ast) == 1
    assert isinstance(ast[0], Text)
    assert ast[0].value == "hello world"
    print("✓ Simple text parsing works")

def test_preset_parsing():
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
    print(f"DEBUG: ast length: {len(ast)}")
    if len(ast) > 0:
        print(f"DEBUG: ast[0] type: {type(ast[0])}")
        print(f"DEBUG: ast[0]: {ast[0]}")
        if hasattr(ast[0], 'key_expr'):
            print(f"DEBUG: ast[0].key_expr: {ast[0].key_expr}")
    assert len(ast) == 1
    assert isinstance(ast[0], PresetExpr)
    assert ast[0].key_expr == "quality#base+hdr"
    
    print("✓ Preset parsing works")

def test_placeholder_parsing():
    """プレースホルダー解析テスト"""
    parser = TemplateParser()
    
    ast = parser.parse("{emotion}")
    assert len(ast) == 1
    assert isinstance(ast[0], Placeholder)
    assert ast[0].name == "emotion"
    assert ast[0].mode == "expand"
    
    # :r はランダム（sample）モード
    ast_r = parser.parse("{emotion:r}")
    assert len(ast_r) == 1
    assert isinstance(ast_r[0], Placeholder)
    assert ast_r[0].name == "emotion"
    assert ast_r[0].mode == "sample"
    
    print("✓ Placeholder parsing works")

def test_wildcard_parsing():
    """ワイルドカード解析テスト"""
    parser = TemplateParser()
    
    ast = parser.parse("__lighting__")
    assert len(ast) == 1
    assert isinstance(ast[0], Wildcard)
    assert ast[0].key == "lighting"
    
    print("✓ Wildcard parsing works")

def test_combined_parsing():
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
    
    print("✓ Combined template parsing works")

def test_empty_template():
    """空テンプレートテスト"""
    parser = TemplateParser()
    
    ast = parser.parse("")
    assert len(ast) == 0
    
    print("✓ Empty template parsing works")

def test_validation():
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
    
    print("✓ Template validation works")

if __name__ == "__main__":
    print("Testing TemplateParser...")
    
    try:
        test_simple_text()
        test_preset_parsing()
        test_placeholder_parsing()
        test_wildcard_parsing()
        test_combined_parsing()
        test_empty_template()
        test_validation()
        
        print("\n✅ All parser tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)