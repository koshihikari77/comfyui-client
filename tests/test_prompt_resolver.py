"""
PromptResolverのテスト
"""
import pytest
import yaml
import tempfile
from pathlib import Path
from unittest.mock import patch

from core.prompt_resolver import PromptResolver


class TestPromptResolver:
    """PromptResolverのテストケース"""
    
    @pytest.fixture
    def temp_prompt_dir(self):
        """プロンプト用の一時ディレクトリを作成"""
        temp_dir = tempfile.mkdtemp()
        prompt_dir = Path(temp_dir)
        
        # presets ディレクトリと内容を作成
        presets_dir = prompt_dir / 'presets'
        presets_dir.mkdir()
        
        # アーキテクチャドキュメントの仕様: プリセットはリスト形式で定義
        quality_preset = [
            'masterpiece',
            'best quality',
            '8K'
        ]
        with open(presets_dir / 'quality.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(quality_preset, f)
            
        character_preset = [
            '1girl',
            'detailed beautiful face and eyes',
            'detailed skin'
        ]
        with open(presets_dir / 'character.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(character_preset, f)
        
        # サブディレクトリのプリセット
        styles_dir = presets_dir / 'styles'
        styles_dir.mkdir()
        anime_preset = [
            'anime style',
            'cel shading',
            'vibrant colors'
        ]
        with open(styles_dir / 'anime.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(anime_preset, f)
        
        # wildcards ディレクトリと内容を作成
        wildcards_dir = prompt_dir / 'wildcards'
        wildcards_dir.mkdir()
        
        # テスト用ワイルドカード
        with open(wildcards_dir / 'colors.txt', 'w', encoding='utf-8') as f:
            f.write('red\nblue\ngreen\nyellow\n')
            
        with open(wildcards_dir / 'animals.txt', 'w', encoding='utf-8') as f:
            f.write('cat\ndog\nbird\nfish\n')
        
        yield prompt_dir
        
        # クリーンアップ
        import shutil
        shutil.rmtree(temp_dir)
    
    def test_initialization_with_valid_directory(self, temp_prompt_dir):
        """正常なディレクトリでの初期化テスト"""
        resolver = PromptResolver(str(temp_prompt_dir))
        
        # プリセットが正しく読み込まれているか確認
        assert 'quality' in resolver._presets
        assert 'character' in resolver._presets
        assert 'styles/anime' in resolver._presets
        assert resolver._presets['quality'] == ['masterpiece', 'best quality', '8K']
        assert resolver._presets['character'] == ['1girl', 'detailed beautiful face and eyes', 'detailed skin']
        
        # ワイルドカードが正しく読み込まれているか確認
        assert 'colors' in resolver._wildcards
        assert 'animals' in resolver._wildcards
        assert 'red' in resolver._wildcards['colors']
        assert 'cat' in resolver._wildcards['animals']
    
    def test_initialization_with_nonexistent_directory(self):
        """存在しないディレクトリでの初期化テスト"""
        resolver = PromptResolver("nonexistent_directory")
        
        # 空の辞書が作成されることを確認
        assert resolver._presets == {}
        assert resolver._wildcards == {}
    
    def test_resolve_simple_text(self, temp_prompt_dir):
        """プレーンテキストの解決テスト"""
        resolver = PromptResolver(str(temp_prompt_dir))
        
        result = resolver.resolve("simple text without any placeholders")
        assert result == "simple text without any placeholders"
    
    def test_resolve_presets(self, temp_prompt_dir):
        """プリセット解決のテスト"""
        resolver = PromptResolver(str(temp_prompt_dir))
        
        # プリセットが展開されることを確認
        result = resolver.resolve("<preset:quality>, <preset:character>")
        assert "masterpiece, best quality, 8K" in result
        assert "1girl, detailed beautiful face and eyes, detailed skin" in result
    
    def test_resolve_hierarchical_presets(self, temp_prompt_dir):
        """階層プリセット解決のテスト"""
        resolver = PromptResolver(str(temp_prompt_dir))
        
        # サブディレクトリのプリセットが展開されることを確認
        result = resolver.resolve("<preset:styles/anime>")
        assert "anime style, cel shading, vibrant colors" in result
    
    def test_resolve_wildcards(self, temp_prompt_dir):
        """ワイルドカード解決のテスト"""
        resolver = PromptResolver(str(temp_prompt_dir))
        
        # ワイルドカードが解決されることを確認（ランダムなので複数回テスト）
        results = []
        for _ in range(10):
            result = resolver.resolve("a __colors__ __animals__")
            results.append(result)
        
        # 少なくとも1回は異なる結果が出ることを期待（ランダム性の確認）
        assert len(set(results)) > 1 or len(results) == 1  # 1回だけの場合も許可
        
        # 有効な色と動物が含まれていることを確認
        sample_result = results[0]
        colors = ['red', 'blue', 'green', 'yellow']
        animals = ['cat', 'dog', 'bird', 'fish']
        
        has_color = any(color in sample_result for color in colors)
        has_animal = any(animal in sample_result for animal in animals)
        assert has_color and has_animal
    
    def test_resolve_combined_presets_and_wildcards(self, temp_prompt_dir):
        """プリセットとワイルドカードの組み合わせテスト"""
        resolver = PromptResolver(str(temp_prompt_dir))
        
        result = resolver.resolve("<preset:character>, wearing __colors__ clothes")
        
        # プリセットが展開されていることを確認
        assert "1girl, detailed beautiful face and eyes, detailed skin" in result
        
        # ワイルドカードが解決されていることを確認
        colors = ['red', 'blue', 'green', 'yellow']
        has_color = any(color in result for color in colors)
        assert has_color
    
    def test_resolve_nonexistent_preset(self, temp_prompt_dir):
        """存在しないプリセットの処理テスト"""
        resolver = PromptResolver(str(temp_prompt_dir))
        
        result = resolver.resolve("test <preset:nonexistent> text")
        
        # 存在しないプリセットはそのまま残ることを確認
        assert "<preset:nonexistent>" in result
    
    def test_resolve_nonexistent_wildcard(self, temp_prompt_dir):
        """存在しないワイルドカードの処理テスト"""
        resolver = PromptResolver(str(temp_prompt_dir))
        
        result = resolver.resolve("test __nonexistent__ text")
        
        # 存在しないワイルドカードはそのまま残ることを確認
        assert "__nonexistent__" in result
    
    def test_text_formatting(self, temp_prompt_dir):
        """テキスト整形のテスト"""
        resolver = PromptResolver(str(temp_prompt_dir))
        
        # カンマと空白が正しく整形されることを確認
        result = resolver.resolve("  item1 ,  item2  , item3  ")
        assert result == "item1, item2, item3"
    
    def test_recursive_preset_resolution(self, temp_prompt_dir):
        """再帰的プリセット解決のテスト"""
        # プリセット内にプリセットを含むテストケースを作成
        recursive_preset = [
            '<preset:character>',
            'extra tag'
        ]
        presets_dir = temp_prompt_dir / 'presets'
        with open(presets_dir / 'recursive.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(recursive_preset, f)
        
        resolver = PromptResolver(str(temp_prompt_dir))
        
        result = resolver.resolve("<preset:recursive>")
        
        # 再帰的に解決されていることを確認
        assert "1girl, detailed beautiful face and eyes, detailed skin" in result
        assert "extra tag" in result
    
    def test_recursion_depth_limit(self, temp_prompt_dir):
        """再帰深度制限のテスト"""
        # 無限再帰を引き起こすプリセットを作成
        infinite_preset = [
            '<preset:infinite>',
            'never_reached'
        ]
        presets_dir = temp_prompt_dir / 'presets'
        with open(presets_dir / 'infinite.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(infinite_preset, f)
        
        resolver = PromptResolver(str(temp_prompt_dir))
        
        # RecursionErrorが発生しないことを確認（エラーハンドリングされる）
        result = resolver.resolve("<preset:infinite>")
        
        # エラー時は元の文字列が返されることを確認
        assert result == "<preset:infinite>"
    
    def test_error_handling_during_resolution(self, temp_prompt_dir):
        """解決中のエラーハンドリングテスト"""
        resolver = PromptResolver(str(temp_prompt_dir))
        
        # 正常なケース
        result = resolver.resolve("normal text")
        assert result == "normal text"
    
    @patch('core.prompt_resolver.logger')
    def test_file_loading_error_handling(self, mock_logger, temp_prompt_dir):
        """ファイル読み込みエラーのハンドリングテスト"""
        # 不正なYAMLファイルを作成
        presets_dir = temp_prompt_dir / 'presets'
        with open(presets_dir / 'invalid.yaml', 'w', encoding='utf-8') as f:
            f.write("invalid: yaml: content: [unclosed")
        
        # エラーログが出力されることを確認
        resolver = PromptResolver(str(temp_prompt_dir))
        
        # エラーログが呼ばれたことを確認
        mock_logger.error.assert_called()
    
    @patch('core.prompt_resolver.logger')
    def test_invalid_preset_format_handling(self, mock_logger, temp_prompt_dir):
        """不正なプリセット形式のハンドリングテスト"""
        # dict形式（旧形式）のプリセットファイルを作成
        presets_dir = temp_prompt_dir / 'presets'
        invalid_preset = {
            'characters': ['Alice', 'Bob']  # dict形式は非サポート
        }
        with open(presets_dir / 'invalid_format.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(invalid_preset, f)
        
        resolver = PromptResolver(str(temp_prompt_dir))
        
        # 警告ログが出力されることを確認
        mock_logger.warning.assert_called()
        
        # 空のリストとして扱われることを確認
        assert resolver._presets['invalid_format'] == []


class TestPromptResolverNewAPI:
    """PromptResolverの新API（resolve_full, expand_placeholders）のテストケース"""
    
    @pytest.fixture
    def temp_prompt_dir(self):
        """プロンプト用の一時ディレクトリを作成"""
        temp_dir = tempfile.mkdtemp()
        prompt_dir = Path(temp_dir)
        
        # presets ディレクトリと内容を作成
        presets_dir = prompt_dir / 'presets'
        presets_dir.mkdir()
        
        quality_preset = ['masterpiece', 'best quality']
        with open(presets_dir / 'quality.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(quality_preset, f)
        
        # wildcards ディレクトリと内容を作成
        wildcards_dir = prompt_dir / 'wildcards'
        wildcards_dir.mkdir()
        
        with open(wildcards_dir / 'colors.txt', 'w', encoding='utf-8') as f:
            f.write('red\nblue\ngreen\n')
        
        yield prompt_dir
        
        # クリーンアップ
        import shutil
        shutil.rmtree(temp_dir)
    
    def test_resolve_full_without_placeholders(self, temp_prompt_dir):
        """プレースホルダーなしでのresolve_full()テスト"""
        resolver = PromptResolver(str(temp_prompt_dir))
        
        # プリセット + ワイルドカードの解決
        result = resolver.resolve_full("<preset:quality>, __colors__ cat")
        
        # プリセットが展開されていることを確認
        assert "masterpiece, best quality" in result
        
        # ワイルドカードが解決されていることを確認
        colors = ['red', 'blue', 'green']
        has_color = any(color in result for color in colors)
        assert has_color
        assert "cat" in result
    
    def test_resolve_full_with_placeholders(self, temp_prompt_dir):
        """プレースホルダーありでのresolve_full()テスト"""
        resolver = PromptResolver(str(temp_prompt_dir))
        
        placeholders = {
            'style': ['anime', 'realistic'],
            'pose': ['standing', 'sitting']
        }
        
        # プリセット + プレースホルダー + ワイルドカードの解決
        result = resolver.resolve_full(
            "<preset:quality>, {style} {pose}, __colors__ dress", 
            placeholders
        )
        
        # プリセットが展開されていることを確認
        assert "masterpiece, best quality" in result
        
        # プレースホルダーが解決されていることを確認
        has_style = any(style in result for style in ['anime', 'realistic'])
        has_pose = any(pose in result for pose in ['standing', 'sitting'])
        assert has_style and has_pose
        
        # ワイルドカードが解決されていることを確認
        colors = ['red', 'blue', 'green']
        has_color = any(color in result for color in colors)
        assert has_color
        assert "dress" in result
    
    def test_resolve_full_error_handling(self, temp_prompt_dir):
        """resolve_full()のエラーハンドリングテスト"""
        resolver = PromptResolver(str(temp_prompt_dir))
        
        # 存在しないプレースホルダーでも元の文字列を返すことを確認
        result = resolver.resolve_full("test {nonexistent} text", {'other': ['value']})
        assert "test {nonexistent} text" in result
    
    def test_expand_placeholders_simple(self, temp_prompt_dir):
        """expand_placeholders()の基本テスト"""
        resolver = PromptResolver(str(temp_prompt_dir))
        
        placeholders = {
            'style': ['anime', 'realistic'],
            'pose': ['standing', 'sitting']
        }
        
        result = resolver.expand_placeholders("1girl, {style}, {pose}", placeholders)
        
        # 4つの組み合わせが生成されることを確認
        expected = [
            "1girl, anime, standing",
            "1girl, anime, sitting", 
            "1girl, realistic, standing",
            "1girl, realistic, sitting"
        ]
        
        assert len(result) == 4
        assert set(result) == set(expected)
    
    def test_expand_placeholders_no_placeholders(self, temp_prompt_dir):
        """プレースホルダーなしのexpand_placeholders()テスト"""
        resolver = PromptResolver(str(temp_prompt_dir))
        
        result = resolver.expand_placeholders("simple text", {})
        assert result == ["simple text"]
    
    def test_expand_placeholders_single_placeholder(self, temp_prompt_dir):
        """単一プレースホルダーのexpand_placeholders()テスト"""
        resolver = PromptResolver(str(temp_prompt_dir))
        
        placeholders = {'style': ['anime', 'realistic', 'cartoon']}
        
        result = resolver.expand_placeholders("1girl, {style} style", placeholders)
        
        expected = [
            "1girl, anime style",
            "1girl, realistic style", 
            "1girl, cartoon style"
        ]
        
        assert len(result) == 3
        assert set(result) == set(expected)
    
    def test_expand_placeholders_missing_key(self, temp_prompt_dir):
        """存在しないプレースホルダーのexpand_placeholders()テスト"""
        resolver = PromptResolver(str(temp_prompt_dir))
        
        placeholders = {'style': ['anime']}
        
        # 存在しないプレースホルダーでValueErrorが発生することを確認
        with pytest.raises(ValueError, match="Placeholder {missing} not found"):
            resolver.expand_placeholders("1girl, {style}, {missing}", placeholders)
    
    def test_expand_placeholders_complex(self, temp_prompt_dir):
        """複雑なプレースホルダー組み合わせテスト"""
        resolver = PromptResolver(str(temp_prompt_dir))
        
        placeholders = {
            'char': ['1girl', '2girls'],
            'hair': ['long hair', 'short hair'],
            'color': ['black', 'brown']
        }
        
        result = resolver.expand_placeholders(
            "{char}, {hair}, {color} hair", 
            placeholders
        )
        
        # 2 * 2 * 2 = 8 の組み合わせが生成されることを確認
        assert len(result) == 8
        
        # いくつかの期待される組み合わせを確認
        assert "1girl, long hair, black hair" in result
        assert "2girls, short hair, brown hair" in result
        
        # すべての組み合わせがユニークであることを確認
        assert len(set(result)) == 8 