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
from .resolver.placeholder import PlaceholderSubstitutor
from .resolver.wildcard import WildcardSubstitutor
from .resolver.filter import TagFilter
from .resolver.formatter import PromptFormatter

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
            reparse_depth=0
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
        Parse → PresetEval → Placeholder → Wildcard → Filter → Format
        
        Args:
            template_string: 解決するテンプレート文字列
            
        Returns:
            解決済みプロンプト文字列
        """
        try:
            logger.debug(f"V2 resolving: '{template_string[:50]}...'")
            
            # ① Parse
            ast = self.parser.parse(template_string)
            
            # ② PresetEval
            ast = self.preset_evaluator.evaluate_ast(ast)
            
            # ③ Placeholder (sampleモード)
            ast = self.placeholder_substitutor.substitute_ast(ast)
            
            # ④ Wildcard
            ast = self.wildcard_substitutor.substitute_ast(ast)
            
            # ⑤ Filter
            tagset = self.tag_filter.filter_ast(ast)
            
            #TagSetが空の場合の処理（soft/warnレベル対応）
            if not tagset:
                logger.debug(f"Empty TagSet for template: '{template_string}', returning original")
                return template_string
            
            # ⑥ Format
            result = self.formatter.format_tagset(tagset)
            
            logger.debug(f"V2 resolved: '{result[:50]}...'")
            return result
            
        except Exception as e:
            logger.error(f"V2 pipeline failed to resolve: '{template_string}'", exc_info=True)
            # エラー時は元文字列を返す（V1互換）
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
                
                # ③ Placeholder (expandモード)
                ast_result = self.placeholder_substitutor.substitute_ast(ast)
                
                # expandモードの場合、listが返される可能性がある
                if isinstance(ast_result, list):
                    ast_list = ast_result
                else:
                    ast_list = [ast_result]
                
                # 各ASTに対して④⑤⑥を実行
                results = []
                for ast in ast_list:
                    # ④ Wildcard
                    ast = self.wildcard_substitutor.substitute_ast(ast)
                    
                    # ⑤ Filter
                    tagset = self.tag_filter.filter_ast(ast)
                    
                    # ⑥ Format
                    result = self.formatter.format_tagset(tagset)
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
        
        logger.debug(f"V2 context updated: {config}")
    
    def get_pipeline_info(self) -> Dict:
        """パイプライン情報取得（デバッグ用）"""
        return {
            "version": "2.0",
            "stages": ["Parse", "PresetEval", "Placeholder", "Wildcard", "Filter", "Format"],
            "presets_count": len(self.context.presets),
            "wildcards_count": len(self.context.wildcards),
            "locale": self.context.locale,
            "strict_level": self.context.strict_level
        }