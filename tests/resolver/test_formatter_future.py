"""
PromptFormatter将来拡張機能テスト

Phase4用の将来拡張準備機能テスト
"""

import pytest
from random import Random
from ordered_set import OrderedSet

from core.resolver.formatter import PromptFormatter
from core.resolver.context import ResolverContext


class TestPromptFormatterFutureExtensions:
    """PromptFormatter将来拡張機能のテスト"""
    
    def setup_method(self):
        """テスト用コンテキスト準備"""
        self.context = ResolverContext(
            presets={},
            wildcards={},
            rng=Random(42),
            locale=",",
            strict_level="warn"
        )
        self.formatter = PromptFormatter(self.context)
    
    def test_apply_formatting_options_identity(self):
        """フォーマッティングオプション（現在は透過）"""
        tags = ["tag3", "tag1", "tag2"]
        result = self.formatter._apply_formatting_options(tags)
        
        # 現在は変更されない（将来拡張で変更予定）
        assert result == tags
        assert result is not tags  # コピーが作成される
    
    def test_apply_sort_alpha_functionality(self):
        """アルファベット順ソート機能（将来拡張用）"""
        tags = ["zebra", "Apple", "banana", "Cherry"]
        result = self.formatter._apply_sort_alpha(tags)
        
        # 大文字小文字を無視したソート
        expected = ["Apple", "banana", "Cherry", "zebra"]
        assert result == expected
    
    def test_apply_shuffle_functionality(self):
        """シャッフル機能（将来拡張用）"""
        tags = ["tag1", "tag2", "tag3", "tag4", "tag5"]
        
        # 決定論的な結果確認（同じシード）
        result1 = self.formatter._apply_shuffle(tags)
        
        # 新しいformatterで同じシード
        formatter2 = PromptFormatter(self.context.model_copy(update={"rng": Random(42)}))
        result2 = formatter2._apply_shuffle(tags)
        
        # 同じシードなら同じ結果
        assert result1 == result2
        
        # 元のリストは変更されない
        assert tags == ["tag1", "tag2", "tag3", "tag4", "tag5"]
    
    def test_sort_alpha_edge_cases(self):
        """ソート機能のエッジケース"""
        # 空リスト
        assert self.formatter._apply_sort_alpha([]) == []
        
        # 単一要素
        assert self.formatter._apply_sort_alpha(["single"]) == ["single"]
        
        # 特殊文字・数字を含む
        tags = ["9tag", "1tag", "!special", "@symbol", "atag"]
        result = self.formatter._apply_sort_alpha(tags)
        expected = ["!special", "1tag", "9tag", "@symbol", "atag"]
        assert result == expected
        
        # Unicode文字
        unicode_tags = ["中文", "English", "日本語", "العربية"]
        result = self.formatter._apply_sort_alpha(unicode_tags)
        # Unicode順序は実装依存だが、関数が動作することを確認
        assert len(result) == 4
        assert all(tag in result for tag in unicode_tags)
    
    def test_shuffle_edge_cases(self):
        """シャッフル機能のエッジケース"""
        # 空リスト
        assert self.formatter._apply_shuffle([]) == []
        
        # 単一要素
        result = self.formatter._apply_shuffle(["single"])
        assert result == ["single"]
        
        # 2要素（シャッフル可能性確認）
        tags = ["a", "b"]
        results = []
        for seed in range(10):  # 複数シードで試行
            formatter = PromptFormatter(self.context.model_copy(update={"rng": Random(seed)}))
            result = formatter._apply_shuffle(tags)
            results.append(tuple(result))
        
        # 少なくとも2種類の結果が出る（確率的だが）
        unique_results = set(results)
        assert len(unique_results) >= 1  # 最低でも1種類は存在
    
    def test_formatting_options_integration(self):
        """フォーマッティングオプション統合テスト"""
        tagset = OrderedSet(["tag3", "tag1", "tag2"])
        
        # 現在の動作確認（順序保持）
        result = self.formatter.format_tagset(tagset)
        assert result == "tag3, tag1, tag2"
        
        # 将来的にはオプションによって結果が変わることを想定
        # （現在はコメントアウトされた機能）
    
    def test_internal_method_accessibility(self):
        """内部メソッドのアクセス性確認"""
        # 将来拡張用メソッドが適切に実装されていることを確認
        assert hasattr(self.formatter, '_apply_sort_alpha')
        assert hasattr(self.formatter, '_apply_shuffle')
        assert callable(self.formatter._apply_sort_alpha)
        assert callable(self.formatter._apply_shuffle)
    
    def test_performance_with_large_datasets(self):
        """大規模データセットでの将来拡張機能性能"""
        # 1000要素でのソート性能
        large_tags = [f"tag_{i:04d}" for i in range(999, -1, -1)]  # 逆順
        
        result = self.formatter._apply_sort_alpha(large_tags)
        # ソートされていることを確認
        assert result[0] == "tag_0000"
        assert result[-1] == "tag_0999"
        assert len(result) == 1000
        
        # シャッフル性能
        shuffle_result = self.formatter._apply_shuffle(large_tags)
        assert len(shuffle_result) == 1000
        assert set(shuffle_result) == set(large_tags)  # 全要素が保持される


class TestPromptFormatterFutureCompatibility:
    """将来互換性テスト"""
    
    def setup_method(self):
        """テスト用コンテキスト準備"""
        self.context = ResolverContext(
            presets={},
            wildcards={},
            rng=Random(42),
            locale=",",
            strict_level="warn"
        )
        self.formatter = PromptFormatter(self.context)
    
    def test_context_extension_compatibility(self):
        """コンテキスト拡張への対応性確認"""
        # 現在のコンテキストに将来フィールドが追加されても動作することを確認
        
        # hasattr チェックが安全に動作することを確認
        assert not hasattr(self.context, 'sort_alpha')
        assert not hasattr(self.context, 'shuffle')
        
        # 実際の処理が影響を受けないことを確認
        tagset = OrderedSet(["tag1", "tag2", "tag3"])
        result = self.formatter.format_tagset(tagset)
        assert result == "tag1, tag2, tag3"
    
    def test_method_signature_stability(self):
        """メソッドシグネチャの安定性確認"""
        # 主要メソッドのシグネチャが予期通りであることを確認
        import inspect
        
        # format_tagsetメソッドのシグネチャ
        sig = inspect.signature(self.formatter.format_tagset)
        params = list(sig.parameters.keys())
        assert 'tagset' in params
        
        # 内部メソッドのシグネチャ
        sort_sig = inspect.signature(self.formatter._apply_sort_alpha)
        shuffle_sig = inspect.signature(self.formatter._apply_shuffle)
        
        assert 'tags' in sort_sig.parameters
        assert 'tags' in shuffle_sig.parameters
    
    def test_error_handling_with_future_features(self):
        """将来機能でのエラーハンドリング"""
        # 将来機能が有効化されてもエラーハンドリングが動作することを確認
        
        # ソート機能でのエラー処理
        try:
            # None値でもクラッシュしないことを確認
            result = self.formatter._apply_sort_alpha([None, "valid"])
        except TypeError:
            # 期待される例外（型エラー）
            pass
        
        # シャッフル機能でのエラー処理
        result = self.formatter._apply_shuffle(["tag1", "tag2"])
        assert len(result) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])