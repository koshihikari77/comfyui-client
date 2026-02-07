"""
PromptResolver V2 - 6ステージパイプライン統合実装

完全に独立したV2実装。既存のPromptResolver(V1)とは分離。
Parse → PresetEval → Placeholder → Wildcard → Filter → Format
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Union
from random import Random

from .interfaces import IPromptResolver
from .resolver.context import ResolverContext, PresetFile
from .resolver.parser import TemplateParser
from .resolver.preset import PresetEvaluator
from .resolver.placeholder import PlaceholderSubstitutor, expand_inline_placeholders
from .resolver.wildcard import WildcardSubstitutor
from .resolver.filter import TagFilter
from .resolver.formatter import PromptFormatter
from .resolver.exceptions import RecursionLimitError

logger = logging.getLogger(__name__)


class PromptResolverV2(IPromptResolver):
    """
    PromptResolver V2 - 6ステージパイプライン実装
    
    完全に独立したV2クラス。V1との互換性を保ちつつ、
    高度な6ステージパイプライン処理を提供。
    
    6ステージ: Parse → PresetEval → Placeholder → Wildcard → Filter → Format
    """
    
    def __init__(self, prompt_dir: str = "prompts", config: Optional[Dict] = None):
        """
        PromptResolverV2初期化
        
        Args:
            prompt_dir: プロンプトファイルのベースディレクトリ
            config: 設定辞書（省略時はデフォルト設定）
        """
        self.base_path = Path(prompt_dir)
        logger.info(f"PromptResolverV2 initializing with base_path: {self.base_path.absolute()}")
        
        # ResolverContext構築
        self.context = self._build_context(config or {})
        
        # 6ステージパイプライン初期化
        self._init_pipeline()
        
        logger.info(f"V2 pipeline initialized - 6 stages ready")
    
    def _build_context(self, config: Dict) -> ResolverContext:
        """設定からResolverContextを構築"""
        # プリセット・ワイルドカード読み込み
        presets = self._load_presets()
        wildcards = self._load_wildcards()
        
        # 設定から値を取得（デフォルト値付き）
        return ResolverContext(
            presets=presets,
            wildcards=wildcards,
            rng=Random(config.get('seed')),
            ignore_tags=set(config.get('ignore_tags', [])),
            ignore_groups=set(config.get('ignore_groups', [])),
            placeholders=config.get('placeholders', {}),
            locale=config.get('locale', ','),
            strict_level=config.get('strict_level', 'warn'),
            reparse_depth=0,
            placeholder_max_expansion=config.get('placeholder_max_expansion', 128),
        )
    
    def _load_presets(self) -> Dict[str, PresetFile]:
        """プリセットファイル読み込み（V2形式対応）"""
        presets = {}
        presets_dir = self.base_path / "presets"
        
        if not presets_dir.is_dir():
            logger.warning(f"Presets directory not found: {presets_dir}")
            return presets
        
        for file_path in presets_dir.rglob('*.yaml'):
            key = str(file_path.relative_to(presets_dir)).replace('.yaml', '').replace('\\', '/')
            try:
                import yaml
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                
                # V1/V2形式の自動判定・変換
                if isinstance(data, list):
                    # V1形式: list → V2形式変換
                    preset_file = PresetFile(
                        version=1,
                        contents={"__all__": data}
                    )
                elif isinstance(data, dict):
                    # V2形式: dict → PresetFile
                    preset_file = PresetFile(**data)
                else:
                    logger.warning(f"Unknown preset format in {file_path}")
                    continue
                
                presets[key] = preset_file
                logger.debug(f"Loaded preset: {key} (v{preset_file.version})")
                
            except Exception as e:
                logger.error(f"Failed to load preset {file_path}: {e}")
        
        logger.info(f"Loaded {len(presets)} presets: {list(presets.keys())}")
        return presets
    
    def _load_wildcards(self) -> Dict[str, List[str]]:
        """ワイルドカードファイル読み込み"""
        wildcards = {}
        wildcards_dir = self.base_path / "wildcards"
        
        if not wildcards_dir.is_dir():
            logger.warning(f"Wildcards directory not found: {wildcards_dir}")
            return wildcards
        
        for file_path in wildcards_dir.rglob('*.txt'):
            key = str(file_path.relative_to(wildcards_dir)).replace('.txt', '').replace('\\', '/')
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = [line.strip() for line in f if line.strip()]
                wildcards[key] = lines
                logger.debug(f"Loaded wildcard: {key} ({len(lines)} entries)")
            except Exception as e:
                logger.error(f"Failed to load wildcard {file_path}: {e}")
        
        logger.info(f"Loaded {len(wildcards)} wildcards: {list(wildcards.keys())}")
        return wildcards
    
    def _init_pipeline(self):
        """6ステージパイプライン初期化"""
        self.parser = TemplateParser()
        self.preset_evaluator = PresetEvaluator(self.context)
        self.placeholder_substitutor = PlaceholderSubstitutor(self.context)
        self.wildcard_substitutor = WildcardSubstitutor(self.context)
        self.tag_filter = TagFilter(self.context)
        self.formatter = PromptFormatter(self.context)
        
        logger.debug("6-stage pipeline components initialized")
    
    def resolve(self, template_string: str) -> str:
        """
        メインの解決メソッド（sampleモード）
        
        6ステージパイプライン実行:
        Parse → PresetEval(統合) → Placeholder → Wildcard → Filter → Format
        
        Args:
            template_string: 解決するテンプレート文字列
            
        Returns:
            解決済みプロンプト文字列
        """
        try:
            logger.debug(f"V2 resolving: '{template_string[:50]}...'")
            
            # ⓪ Inline placeholder 前処理 ({a | b | c} → {_inline_N})
            original_ph = self.context.placeholders
            local_ph = dict(original_ph)
            template_string, local_ph, _ = expand_inline_placeholders(
                template_string, local_ph
            )
            self.context.placeholders = local_ph
            try:
                # ① Parse
                ast = self.parser.parse(template_string)
                
                # ② PresetEval (ネスト処理統合済み)
                ast = self.preset_evaluator.evaluate_ast(ast)
                
                # ③ PresetSubst (統合によりスキップ)
                # ast = self.preset_substitutor.substitute_ast(ast)
                
                # ④ Placeholder（混在: expand は n 番目、sample(:r) はランダム。n=0 で API 互換）
                ast = self.placeholder_substitutor.substitute_mixed_nth(
                    ast, 0, cycle=True, max_expansion=self.context.placeholder_max_expansion
                )
                
                # ⑤ Wildcard
                ast = self.wildcard_substitutor.substitute_ast(ast)
                
                # ⑥ Filter
                tagset = self.tag_filter.filter_ast(ast)
                
                #TagSetが空の場合の処理（soft/warnレベル対応）
                if not tagset:
                    logger.debug(f"Empty TagSet for template: '{template_string}', returning original")
                    return template_string
                
                # ⑦ Format
                result = self.formatter.format_tagset(tagset)
                
                logger.debug(f"V2 resolved: '{result[:50]}...'")
                return result
            finally:
                self.context.placeholders = original_ph
            
        except Exception as e:
            logger.error(f"V2 pipeline failed to resolve: '{template_string}'", exc_info=True)
            # エラー時は元文字列を返す（V1互換）
            return template_string
    
    def resolve_nth(
        self,
        template_string: str,
        n: int,
        cycle: bool = True,
        placeholders: Optional[Dict] = None,
    ) -> str:
        """
        n 番目の直積組み合わせで解決（Sequence や dump-prompts 用）。
        expand は n 番目を選択、sample(:r) はランダム。cycle=True なら n を combo_count で剰余。
        
        Args:
            template_string: テンプレート文字列
            n: 組み合わせインデックス（0-based）
            cycle: True のとき n を組み合わせ数で剰余する
            placeholders: 一時的に使うプレースホルダー辞書（省略時は context のまま）
            
        Returns:
            解決済みプロンプト文字列
        """
        try:
            original = self.context.placeholders
            if placeholders is not None:
                self.context.placeholders = placeholders
            try:
                # ⓪ Inline placeholder 前処理
                local_ph = dict(self.context.placeholders)
                template_string, local_ph, _ = expand_inline_placeholders(
                    template_string, local_ph
                )
                self.context.placeholders = local_ph

                ast = self.parser.parse(template_string)
                ast = self.preset_evaluator.evaluate_ast(ast)
                ast = self.placeholder_substitutor.substitute_mixed_nth(
                    ast, n, cycle=cycle, max_expansion=self.context.placeholder_max_expansion
                )
                ast = self.wildcard_substitutor.substitute_ast(ast)
                tagset = self.tag_filter.filter_ast(ast)
                if not tagset:
                    return template_string
                return self.formatter.format_tagset(tagset)
            finally:
                self.context.placeholders = original
        except Exception as e:
            logger.error(f"V2 resolve_nth failed: n={n} '{template_string}'", exc_info=True)
            return template_string
    
    def resolve_full(self, template: str, placeholders: Optional[Dict] = None) -> str:
        """
        プレースホルダー付き解決（V1互換インターフェース）
        
        Args:
            template: テンプレート文字列
            placeholders: プレースホルダー辞書
            
        Returns:
            解決済みプロンプト文字列
        """
        try:
            if placeholders:
                # 一時的にコンテキストにプレースホルダーを設定
                original_placeholders = self.context.placeholders
                self.context.placeholders = placeholders
                try:
                    return self.resolve(template)
                finally:
                    self.context.placeholders = original_placeholders
            else:
                return self.resolve(template)
                
        except Exception as e:
            logger.error(f"V2 resolve_full failed: '{template}'", exc_info=True)
            return template
    
    def expand_placeholders(self, template: str, placeholders: Dict) -> List[str]:
        """
        プレースホルダー全組み合わせ展開（expandモード）
        
        Args:
            template: テンプレート文字列
            placeholders: プレースホルダー辞書
            
        Returns:
            展開済みプロンプト文字列のリスト
        """
        try:
            logger.debug(f"V2 expanding: '{template[:50]}...' with {len(placeholders)} placeholders")
            
            # 一時的にコンテキストにプレースホルダーを設定
            original_placeholders = self.context.placeholders
            self.context.placeholders = placeholders
            
            try:
                # ① Parse
                ast = self.parser.parse(template)
                # ② PresetEval
                ast = self.preset_evaluator.evaluate_ast(ast)
                # ③ expand 組み合わせ数に応じて n 番目を列挙（真に全組合せ）
                combo_count = self.placeholder_substitutor.count_expand_combinations(ast)
                max_exp = self.context.placeholder_max_expansion
                if combo_count > max_exp:
                    raise RecursionLimitError(
                        f"Placeholder expansion too large: {combo_count} > {max_exp}",
                        depth=combo_count,
                    )
                results = []
                for n in range(combo_count):
                    ast_n = self.placeholder_substitutor.substitute_mixed_nth(
                        ast, n, cycle=False, max_expansion=max_exp
                    )
                    ast_n = self.wildcard_substitutor.substitute_ast(ast_n)
                    tagset = self.tag_filter.filter_ast(ast_n)
                    result = self.formatter.format_tagset(tagset) if tagset else template
                    results.append(result)
                logger.debug(f"V2 expanded into {len(results)} variations")
                return results
                
            finally:
                self.context.placeholders = original_placeholders
                
        except Exception as e:
            logger.error(f"V2 expand_placeholders failed: '{template}'", exc_info=True)
            # エラー時は元テンプレートのリストを返す（V1互換）
            return [template]
    
    def update_config(self, config: Dict):
        """実行時設定更新"""
        if 'ignore_tags' in config:
            self.context.ignore_tags = set(config['ignore_tags'])
        
        if 'ignore_groups' in config:
            self.context.ignore_groups = set(config['ignore_groups'])
        
        if 'locale' in config:
            self.context.locale = config['locale']
        
        if 'strict_level' in config:
            self.context.strict_level = config['strict_level']
        
        if 'seed' in config:
            self.context.rng = Random(config['seed'])
        if 'placeholder_max_expansion' in config:
            self.context.placeholder_max_expansion = config['placeholder_max_expansion']
        
    def get_preset_groups(self, preset_key: str) -> List[str]:
        """
        指定されたプリセットの全グループ名を定義順で返す
        
        Args:
            preset_key: プリセット名（例: "character/akira"）
        
        Returns:
            グループ名のリスト（例: ["1", "pre_fella_sad"]）
        
        Raises:
            KeyError: プリセットが存在しない場合
            ValueError: プリセット内容が不正な場合
        """
        if preset_key not in self.context.presets:
            raise KeyError(f"Preset '{preset_key}' not found")
        
        preset_file = self.context.presets[preset_key]
        
        if not hasattr(preset_file, 'contents') or not preset_file.contents:
            raise ValueError(f"Preset '{preset_key}' has no contents")
        
        # contentsのキーを定義順で返す（辞書の挿入順序はPython 3.7+で保証）
        group_names = list(preset_file.contents.keys())
        
        logger.debug(f"get_preset_groups: '{preset_key}' -> {group_names}")
        return group_names
    
    def get_pipeline_info(self) -> Dict:
        """パイプライン情報取得（デバッグ用）"""
        return {
            "version": "2.0",
            "stages": ["Parse", "PresetEval(統合)", "Placeholder", "Wildcard", "Filter", "Format"],
            "presets_count": len(self.context.presets),
            "wildcards_count": len(self.context.wildcards),
            "locale": self.context.locale,
            "strict_level": self.context.strict_level
        }