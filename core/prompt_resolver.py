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

    def resolve_full(self, template: str, placeholders: dict | None = None) -> str:
        """Preset → Placeholder → Wildcard の順で 1 つの文字列を解決"""
        try:
            # 1. プリセットを解決
            resolved_presets = self._resolve_presets(template)
            
            # 2. プレースホルダーを解決（もし提供されていれば）
            if placeholders:
                resolved_placeholders = self._resolve_placeholders(resolved_presets, placeholders)
            else:
                resolved_placeholders = resolved_presets
            
            # 3. ワイルドカードを解決
            final_string = self._resolve_wildcards(resolved_placeholders)
            
            # 4. カンマや空白を整形
            return ", ".join(filter(None, [tag.strip() for tag in final_string.split(',')]))
        except Exception as e:
            logger.error(f"Failed to resolve full template: '{template}'", exc_info=True)
            return template

    def expand_placeholders(self, template: str, placeholders: dict) -> list[str]:
        """プレースホルダーの全組合せを生成"""
        import itertools
        
        # 1. テンプレートからプレースホルダー名を抽出
        placeholder_names = re.findall(r'{(.*?)}', template)
        if not placeholder_names:
            return [template]
        
        # 2. 各プレースホルダーの値リストを取得
        try:
            value_lists = [placeholders[name] for name in placeholder_names]
        except KeyError as e:
            raise ValueError(f"Placeholder {{{e.args[0]}}} not found in placeholders definition.")
        
        # 3. 値の全組み合わせを生成
        combinations = list(itertools.product(*value_lists))
        
        # 4. 各組み合わせを元のテンプレートに埋め込んで最終的な文字列リストを作成
        expanded_strings = []
        for combo in combinations:
            temp_string = template
            for name, value in zip(placeholder_names, combo):
                temp_string = temp_string.replace(f'{{{name}}}', str(value), 1)
            expanded_strings.append(temp_string)
        
        logger.debug(f"Expanded template '{template[:30]}...' into {len(expanded_strings)} prompts.")
        return expanded_strings

    def _resolve_placeholders(self, text: str, placeholders: dict) -> str:
        """単一文字列のプレースホルダーをランダムに置換"""
        placeholder_names = re.findall(r'{(.*?)}', text)
        
        for name in placeholder_names:
            if name in placeholders and placeholders[name]:
                replacement = random.choice(placeholders[name])
                text = text.replace(f'{{{name}}}', str(replacement), 1)
            else:
                logger.warning(f"Placeholder {{{name}}} not found or empty.")
        
        return text

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
