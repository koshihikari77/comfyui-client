import os
import random
import re
from pathlib import Path
import yaml
import logging
from .interfaces import IPromptResolver

logger = logging.getLogger(__name__)

class PromptResolver(IPromptResolver):
    def __init__(self, prompt_dir="prompts"):
        self.base_path = Path(prompt_dir)
        logger.info(f"PromptResolver initializing with base_path: {self.base_path.absolute()}")
        self._presets = self._load_definitions(self.base_path / "presets", ".yaml")
        self._wildcards = self._load_definitions(self.base_path / "wildcards", ".txt")
        logger.info(f"Loaded {len(self._presets)} presets: {list(self._presets.keys())}")
        logger.info(f"Loaded {len(self._wildcards)} wildcards: {list(self._wildcards.keys())}")

    def _load_definitions(self, path: Path, extension: str) -> dict:
        definitions = {}
        if not path.is_dir():
            return definitions
        for file_path in path.rglob(f'*{extension}'):
            key = str(file_path.relative_to(path)).replace(extension, '').replace(os.path.sep, '/')
            try:
                if extension == '.yaml':
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                        # アーキテクチャドキュメントの仕様: プリセットはリスト形式で定義される
                        if isinstance(data, list):
                            definitions[key] = data
                        else:
                            logger.warning(f"Preset file {file_path} should contain a list, got {type(data).__name__}")
                            definitions[key] = []
                elif extension == '.txt':
                    with open(file_path, 'r', encoding='utf-8') as f:
                        definitions[key] = [line.strip() for line in f if line.strip()]
            except Exception as e:
                logger.error(f"Failed to load definition file {file_path}: {e}")
        return definitions

    def resolve(self, template_string: str) -> str:
        """プリセットを解決し、次にワイルドカードを解決する"""
        try:
            # 1. プリセットを解決
            resolved_presets = self._resolve_presets(template_string)
            # 2. ワイルドカードを解決
            final_string = self._resolve_wildcards(resolved_presets)
            # 3. カンマや空白を整形
            return ", ".join(filter(None, [tag.strip() for tag in final_string.split(',')]))
        except Exception as e:
            logger.error(f"Failed to resolve prompt template: '{template_string}'", exc_info=True)
            return template_string # エラー時は元文字列を返す

    def _resolve_presets(self, text: str, depth=0) -> str:
        if depth > 10:  # 無限再帰防止
            raise RecursionError("Preset resolution depth exceeded 10.")
        
        pattern = re.compile(r'<preset:(.*?)>')
        match = pattern.search(text)
        if not match:
            return text

        key = match.group(1)
        
        try:
            # アーキテクチャドキュメントの仕様: 単純なキー名でアクセス
            if key in self._presets:
                preset_value = self._presets[key]
                # プリセットの値をカンマで連結して文字列にする
                if isinstance(preset_value, list):
                    replacement = ", ".join(str(item) for item in preset_value)
                else:
                    replacement = str(preset_value)
                
                # 再帰的に解決を続ける
                return self._resolve_presets(text.replace(match.group(0), replacement, 1), depth + 1)
            else:
                logger.warning(f"Preset <{key}> not found. Leaving it as is.")
                # 見つからない場合はそのままにして、次のマッチを探す
                return text[:match.end()] + self._resolve_presets(text[match.end():], depth)
        except (KeyError, TypeError):
            logger.warning(f"Preset <{key}> not found. Leaving it as is.")
            # 見つからない場合はそのままにして、次のマッチを探す
            return text[:match.end()] + self._resolve_presets(text[match.end():], depth)

    def _resolve_wildcards(self, text: str) -> str:
        pattern = re.compile(r'__(.*?)__')
        
        # finditerですべてのマッチを一度に見つける
        matches = list(pattern.finditer(text))
        
        # 後ろから置換していくことで、インデックスのズレを防ぐ
        for match in reversed(matches):
            key = match.group(1)
            if key in self._wildcards and self._wildcards[key]:
                replacement = random.choice(self._wildcards[key])
                text = text[:match.start()] + replacement + text[match.end():]
            else:
                logger.warning(f"Wildcard __{key}__ not found or empty.")
        return text
