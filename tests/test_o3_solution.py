#!/usr/bin/env python3
"""
o3提案解決策の検証テスト
"""

from core.resolver.parser import TemplateParser

def test_o3_solution():
    parser = TemplateParser()
    
    # o3提案のテストケース
    test_cases = [
        ('some_tag', ['Text']),
        ('__lighting__', ['Wildcard']),
        ('prefix __wild__ suffix', ['Text', 'Wildcard', 'Text']),
        ('another_underscore_test', ['Text']),
        ('<preset:quality#base+hdr>, {emotion} girl, __lighting__', ['PresetExpr', 'Text', 'Placeholder', 'Text', 'Wildcard'])
    ]
    
    print('=== o3提案解決策の検証 ===')
    success_count = 0
    
    for tpl, expected in test_cases:
        try:
            ast = parser.parse(tpl)
            types = [node.__class__.__name__ for node in ast]
            
            if types == expected:
                status = 'OK'
                success_count += 1
            else:
                status = 'NG'
                
            print(f'{status} "{tpl}"')
            print(f'  期待: {expected}')
            print(f'  実際: {types}')
            
            if types != expected:
                print(f'  詳細: {[str(node) for node in ast]}')
            print()
            
        except Exception as e:
            print(f'ERROR "{tpl}" → {e}')
            print()
    
    print(f'成功率: {success_count}/{len(test_cases)}')
    return success_count == len(test_cases)

if __name__ == "__main__":
    test_o3_solution()