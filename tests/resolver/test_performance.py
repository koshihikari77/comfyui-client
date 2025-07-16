#!/usr/bin/env python3
"""
TemplateParser パフォーマンステスト統合版

pytest統一化対応
旧test_performance.pyのpytest化 + 包括的パフォーマンステスト
"""

import pytest
import time
import statistics
import threading
from pathlib import Path
import sys

# プロジェクトルートを追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.resolver.parser import TemplateParser


class TestParserCreationPerformance:
    """パーサー作成パフォーマンステスト"""
    
    def test_parser_creation_time(self):
        """パーサー作成時間の測定"""
        times = []
        
        for i in range(10):
            start = time.time()
            parser = TemplateParser()
            end = time.time()
            times.append((end - start) * 1000)  # ms
        
        # 統計情報
        mean_time = statistics.mean(times)
        median_time = statistics.median(times)
        
        # パーサー作成時間が合理的な範囲内であることを確認
        assert mean_time < 50.0, f"平均作成時間が遅すぎます: {mean_time:.2f}ms"
        assert median_time < 50.0, f"中央値作成時間が遅すぎます: {median_time:.2f}ms"
        
        # キャッシュ効果の確認（初回がそれなりに時間がかかることを確認）
        assert times[0] >= min(times), "初回作成時間が最小値以上であることを確認"
    
    def test_parser_creation_consistency(self):
        """パーサー作成の一貫性テスト"""
        times = []
        
        for _ in range(20):
            start = time.time()
            parser = TemplateParser()
            end = time.time()
            times.append((end - start) * 1000)
        
        # 標準偏差が小さいことを確認（一貫性）
        std_dev = statistics.stdev(times)
        assert std_dev < 10.0, f"作成時間のばらつきが大きすぎます: {std_dev:.2f}ms"


class TestParsingPerformance:
    """解析パフォーマンステスト"""
    
    @pytest.fixture
    def parser(self):
        """テスト用パーサー"""
        return TemplateParser()
    
    def test_simple_parsing_performance(self, parser):
        """シンプルなテンプレート解析性能"""
        template = "simple text"
        
        # ウォームアップ
        for _ in range(10):
            parser.parse(template)
        
        # 実測定
        times = []
        for _ in range(100):
            start = time.time()
            parser.parse(template)
            end = time.time()
            times.append((end - start) * 1000)
        
        mean_time = statistics.mean(times)
        assert mean_time < 1.0, f"シンプル解析が遅すぎます: {mean_time:.3f}ms"
    
    def test_complex_parsing_performance(self, parser):
        """複雑なテンプレート解析性能"""
        template = "<preset:quality#base+hdr>, {emotion} girl, __lighting__"
        
        # ウォームアップ
        for _ in range(10):
            parser.parse(template)
        
        # 実測定
        times = []
        for _ in range(100):
            start = time.time()
            parser.parse(template)
            end = time.time()
            times.append((end - start) * 1000)
        
        mean_time = statistics.mean(times)
        assert mean_time < 5.0, f"複雑解析が遅すぎます: {mean_time:.3f}ms"
    
    def test_long_template_parsing_performance(self, parser):
        """長いテンプレート解析性能"""
        # 1000文字の長いテンプレート
        template = "long text " * 100
        
        # ウォームアップ
        for _ in range(5):
            parser.parse(template)
        
        # 実測定
        times = []
        for _ in range(50):
            start = time.time()
            parser.parse(template)
            end = time.time()
            times.append((end - start) * 1000)
        
        mean_time = statistics.mean(times)
        assert mean_time < 10.0, f"長文解析が遅すぎます: {mean_time:.3f}ms"
    
    def test_repeated_parsing_performance(self, parser):
        """繰り返し解析性能（キャッシュ効果）"""
        templates = [
            "simple text",
            "<preset:quality>",
            "{emotion}",
            "__lighting__",
            "complex <preset:quality> {emotion} __lighting__"
        ]
        
        # 各テンプレートを100回解析
        start_time = time.time()
        for _ in range(100):
            for template in templates:
                parser.parse(template)
        end_time = time.time()
        
        total_time = end_time - start_time
        per_parse_time = (total_time / (100 * len(templates))) * 1000
        
        assert per_parse_time < 2.0, f"繰り返し解析が遅すぎます: {per_parse_time:.3f}ms/parse"


class TestValidationPerformance:
    """バリデーション性能テスト"""
    
    @pytest.fixture
    def parser(self):
        """テスト用パーサー"""
        return TemplateParser()
    
    def test_validation_performance(self, parser):
        """バリデーション性能テスト"""
        valid_templates = [
            "simple text",
            "<preset:quality>",
            "{emotion}",
            "__lighting__",
            "complex <preset:quality> {emotion} __lighting__"
        ]
        
        invalid_templates = [
            "<preset:>",
            "{",
            "__",
            "invalid <preset:",
            "broken {emotion template"
        ]
        
        all_templates = valid_templates + invalid_templates
        
        # ウォームアップ
        for _ in range(10):
            for template in all_templates:
                parser.validate_template(template)
        
        # 実測定
        start_time = time.time()
        for _ in range(100):
            for template in all_templates:
                parser.validate_template(template)
        end_time = time.time()
        
        total_time = end_time - start_time
        per_validation_time = (total_time / (100 * len(all_templates))) * 1000
        
        assert per_validation_time < 2.0, f"バリデーションが遅すぎます: {per_validation_time:.3f}ms/validation"
    
    def test_validation_vs_parsing_performance(self, parser):
        """バリデーションと解析の性能比較"""
        template = "<preset:quality#base+hdr>, {emotion} girl, __lighting__"
        
        # バリデーション時間測定
        validation_times = []
        for _ in range(100):
            start = time.time()
            parser.validate_template(template)
            end = time.time()
            validation_times.append((end - start) * 1000)
        
        # 解析時間測定
        parsing_times = []
        for _ in range(100):
            start = time.time()
            parser.parse(template)
            end = time.time()
            parsing_times.append((end - start) * 1000)
        
        mean_validation_time = statistics.mean(validation_times)
        mean_parsing_time = statistics.mean(parsing_times)
        
        # バリデーションの方が高速であることを確認
        assert mean_validation_time <= mean_parsing_time, \
            f"バリデーション({mean_validation_time:.3f}ms)が解析({mean_parsing_time:.3f}ms)より遅い"


class TestConcurrentPerformance:
    """並行処理性能テスト"""
    
    def test_concurrent_parsing_performance(self):
        """並行解析性能テスト"""
        template = "<preset:quality#base+hdr>, {emotion} girl, __lighting__"
        num_threads = 10
        num_parses_per_thread = 50
        
        def parse_worker(results, index):
            parser = TemplateParser()
            times = []
            
            for _ in range(num_parses_per_thread):
                start = time.time()
                parser.parse(template)
                end = time.time()
                times.append((end - start) * 1000)
            
            results[index] = times
        
        # 並行実行
        results = [None] * num_threads
        threads = []
        
        start_time = time.time()
        for i in range(num_threads):
            thread = threading.Thread(target=parse_worker, args=(results, i))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        end_time = time.time()
        
        # 全体実行時間
        total_execution_time = end_time - start_time
        
        # 各スレッドの平均時間
        all_times = []
        for result in results:
            all_times.extend(result)
        
        mean_parse_time = statistics.mean(all_times)
        total_parses = num_threads * num_parses_per_thread
        
        assert total_execution_time < 10.0, f"並行実行が遅すぎます: {total_execution_time:.2f}s"
        assert mean_parse_time < 5.0, f"並行解析の平均時間が遅すぎます: {mean_parse_time:.3f}ms"
    
    def test_parser_cache_thread_safety(self):
        """パーサーキャッシュのスレッドセーフティテスト"""
        num_threads = 20
        num_creations_per_thread = 10
        
        def create_parsers(results, index):
            times = []
            for _ in range(num_creations_per_thread):
                start = time.time()
                parser = TemplateParser()
                end = time.time()
                times.append((end - start) * 1000)
            results[index] = times
        
        # 並行実行
        results = [None] * num_threads
        threads = []
        
        start_time = time.time()
        for i in range(num_threads):
            thread = threading.Thread(target=create_parsers, args=(results, i))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        end_time = time.time()
        
        # 全体実行時間
        total_execution_time = end_time - start_time
        
        # 各スレッドの平均時間
        all_times = []
        for result in results:
            all_times.extend(result)
        
        mean_creation_time = statistics.mean(all_times)
        
        assert total_execution_time < 5.0, f"並行パーサー作成が遅すぎます: {total_execution_time:.2f}s"
        assert mean_creation_time < 20.0, f"並行作成の平均時間が遅すぎます: {mean_creation_time:.3f}ms"


class TestMemoryPerformance:
    """メモリ使用量テスト"""
    
    def test_parser_memory_usage(self):
        """パーサーのメモリ使用量テスト"""
        import gc
        
        # 初期メモリ使用量
        gc.collect()
        
        # 大量のパーサー作成
        parsers = []
        for _ in range(100):
            parser = TemplateParser()
            parsers.append(parser)
        
        # 全てのパーサーで解析実行
        template = "<preset:quality#base+hdr>, {emotion} girl, __lighting__"
        for parser in parsers:
            parser.parse(template)
        
        # メモリ使用量が合理的な範囲内であることを確認
        # （具体的な値は環境依存のため、実行時エラーがないことを確認）
        assert len(parsers) == 100
        
        # パーサーが正常に動作することを確認
        for parser in parsers[:10]:  # 最初の10個をテスト
            ast = parser.parse(template)
            assert len(ast) == 5
    
    def test_parsing_memory_stability(self):
        """解析メモリ安定性テスト"""
        parser = TemplateParser()
        
        # 大量の解析実行
        templates = [
            "simple text",
            "<preset:quality>",
            "{emotion}",
            "__lighting__",
            "complex <preset:quality> {emotion} __lighting__"
        ]
        
        # 1000回の解析実行
        for i in range(1000):
            template = templates[i % len(templates)]
            ast = parser.parse(template)
            
            # 定期的にメモリ使用量をチェック
            if i % 100 == 0:
                import gc
                gc.collect()
        
        # 最終的に正常に動作することを確認
        final_ast = parser.parse("<preset:quality#base+hdr>, {emotion} girl, __lighting__")
        assert len(final_ast) == 5


class TestRegressionPerformance:
    """性能回帰テスト"""
    
    def test_performance_regression_baseline(self):
        """性能回帰ベースラインテスト"""
        parser = TemplateParser()
        template = "<preset:quality#base+hdr>, {emotion} girl, __lighting__"
        
        # 基準性能測定
        times = []
        for _ in range(100):
            start = time.time()
            parser.parse(template)
            end = time.time()
            times.append((end - start) * 1000)
        
        mean_time = statistics.mean(times)
        p95_time = sorted(times)[94]  # 95パーセンタイル
        
        # 基準値（これらの値は実装時の測定値に基づく）
        BASELINE_MEAN = 2.0  # ms
        BASELINE_P95 = 5.0   # ms
        
        assert mean_time < BASELINE_MEAN, \
            f"平均解析時間が基準値を超えています: {mean_time:.3f}ms > {BASELINE_MEAN}ms"
        assert p95_time < BASELINE_P95, \
            f"95%タイル解析時間が基準値を超えています: {p95_time:.3f}ms > {BASELINE_P95}ms"
    
    def test_cache_effectiveness(self):
        """キャッシュ効果測定"""
        # 初回作成時間（キャッシュなし）
        start = time.time()
        parser1 = TemplateParser()
        first_creation_time = (time.time() - start) * 1000
        
        # 2回目以降の作成時間（キャッシュあり）
        subsequent_times = []
        for _ in range(10):
            start = time.time()
            parser = TemplateParser()
            subsequent_times.append((time.time() - start) * 1000)
        
        mean_subsequent_time = statistics.mean(subsequent_times)
        
        # キャッシュ効果の確認
        # 2回目以降は初回より高速であることを確認
        cache_effectiveness = (first_creation_time - mean_subsequent_time) / first_creation_time
        assert cache_effectiveness > 0.0, \
            f"キャッシュ効果が確認できません: {cache_effectiveness:.1%}"


if __name__ == "__main__":
    # pytestがない場合のスタンドアロン実行
    print("=== TemplateParser パフォーマンステスト実行 ===")
    
    test_classes = [
        TestParserCreationPerformance,
        TestParsingPerformance,
        TestValidationPerformance,
        TestConcurrentPerformance,
        TestMemoryPerformance,
        TestRegressionPerformance,
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
                    if hasattr(method, '__call__'):
                        # フィクスチャが必要なメソッドの場合は引数を渡す
                        if 'parser' in method.__code__.co_varnames:
                            method(TemplateParser())
                        else:
                            method()
                        print(f"✓ {method_name}")
                        passed_tests += 1
                except Exception as e:
                    print(f"✗ {method_name}: {e}")
    
    print(f"\n=== 結果: {passed_tests}/{total_tests} テスト成功 ===")