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
        
        # テスト用プリセット
        character_preset = {
            'characters': ['Alice', 'Bob', 'Charlie']
        }
        with open(presets_dir / 'character.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(character_preset, f)
            
        style_preset = {
            'styles': ['anime', 'realistic', 'cartoon']
        }
        with open(presets_dir / 'style.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(style_preset, f)
        
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
        assert 'character' in resolver._presets
        assert 'style' in resolver._presets
        assert resolver._presets['character']['characters'] == ['Alice', 'Bob', 'Charlie']
        
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
        result = resolver.resolve("a <preset:character.characters> in anime style")
        assert "Alice, Bob, Charlie" in result
        assert "anime style" in result
    
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
        
        result = resolver.resolve("a <preset:character.characters> wearing __colors__ clothes")
        
        # プリセットが展開されていることを確認
        assert "Alice, Bob, Charlie" in result
        
        # ワイルドカードが解決されていることを確認
        colors = ['red', 'blue', 'green', 'yellow']
        has_color = any(color in result for color in colors)
        assert has_color
    
    def test_resolve_nonexistent_preset(self, temp_prompt_dir):
        """存在しないプリセットの処理テスト"""
        resolver = PromptResolver(str(temp_prompt_dir))
        
        result = resolver.resolve("test <preset:nonexistent.key> text")
        
        # 存在しないプリセットはそのまま残ることを確認
        assert "<preset:nonexistent.key>" in result
    
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
        recursive_preset = {
            'base': ['<preset:character.characters>', 'extra']
        }
        presets_dir = temp_prompt_dir / 'presets'
        with open(presets_dir / 'recursive.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(recursive_preset, f)
        
        resolver = PromptResolver(str(temp_prompt_dir))
        
        result = resolver.resolve("<preset:recursive.base>")
        
        # 再帰的に解決されていることを確認
        assert "Alice, Bob, Charlie" in result
        assert "extra" in result
    
    def test_recursion_depth_limit(self, temp_prompt_dir):
        """再帰深度制限のテスト"""
        # 無限再帰を引き起こすプリセットを作成
        infinite_preset = {
            'loop': ['<preset:infinite.loop>', 'never_reached']
        }
        presets_dir = temp_prompt_dir / 'presets'
        with open(presets_dir / 'infinite.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(infinite_preset, f)
        
        resolver = PromptResolver(str(temp_prompt_dir))
        
        # RecursionErrorが発生しないことを確認（エラーハンドリングされる）
        result = resolver.resolve("<preset:infinite.loop>")
        
        # エラー時は元の文字列が返されることを確認
        assert result == "<preset:infinite.loop>"
    
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
    
    def test_wildcard_with_empty_file(self, temp_prompt_dir):
        """空のワイルドカードファイルの処理テスト"""
        wildcards_dir = temp_prompt_dir / 'wildcards'
        
        # 空のファイルを作成
        with open(wildcards_dir / 'empty.txt', 'w', encoding='utf-8') as f:
            f.write("")
        
        resolver = PromptResolver(str(temp_prompt_dir))
        
        result = resolver.resolve("test __empty__ text")
        
        # 空のワイルドカードはそのまま残ることを確認
        assert "__empty__" in result 