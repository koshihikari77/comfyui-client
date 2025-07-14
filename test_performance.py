#!/usr/bin/env python3
"""
TemplateParser パフォーマンステスト
"""

import time
import statistics
from core.resolver.parser import TemplateParser

def measure_parser_creation():
    """パーサー作成時間の測定"""
    print("=== パーサー作成時間測定 ===")
    
    times = []
    for i in range(10):
        start = time.time()
        parser = TemplateParser()
        end = time.time()
        times.append((end - start) * 1000)
        print(f"  {i+1}回目: {times[-1]:.2f}ms")
    
    print(f"\n平均時間: {statistics.mean(times):.2f}ms")
    print(f"最小時間: {min(times):.2f}ms")
    print(f"最大時間: {max(times):.2f}ms")
    print(f"標準偏差: {statistics.stdev(times):.2f}ms")
    
    return times

def measure_parsing_performance():
    """パース性能の測定"""
    print("\n=== パース性能測定 ===")
    
    parser = TemplateParser()
    test_templates = [
        "simple text",
        "<preset:quality>",
        "{emotion}",
        "__lighting__",
        "<preset:quality#base+hdr>, {emotion} girl, __lighting__",
        "complex template with <preset:style#anime+hdr>, multiple {character} types, and __background__ elements",
    ]
    
    for template in test_templates:
        times = []
        for _ in range(100):  # 100回実行
            start = time.time()
            ast = parser.parse(template)
            end = time.time()
            times.append((end - start) * 1000)
        
        avg_time = statistics.mean(times)
        print(f"Template: {template[:30]:<30} | Avg: {avg_time:.3f}ms | Nodes: {len(ast)}")

def measure_concurrent_access():
    """並行アクセス性能の測定"""
    print("\n=== 並行アクセス測定 ===")
    
    import threading
    import concurrent.futures
    
    def create_and_parse():
        parser = TemplateParser()
        return parser.parse("<preset:quality>, {emotion}, __lighting__")
    
    # 10スレッドで同時実行
    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(create_and_parse) for _ in range(20)]
        results = [f.result() for f in futures]
    end = time.time()
    
    print(f"20回の並行処理時間: {(end - start) * 1000:.2f}ms")
    print(f"全ての結果が同一: {all(len(r) == len(results[0]) for r in results)}")

if __name__ == "__main__":
    measure_parser_creation()
    measure_parsing_performance()
    measure_concurrent_access()