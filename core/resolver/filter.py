"""
PromptResolver V2 TagFilter実装

設計書4.5に基づくTagLeaf → TagSet変換機能
AST内のTagLeafノードを統合し、ignore_tags適用でTagSetを生成
"""

import logging
from typing import Set
from ordered_set import OrderedSet

from .ast import TemplateAST, ASTNode, TagLeaf, Text
from .context import ResolverContext
from .exceptions import TagFilterError

logger = logging.getLogger(__name__)


class TagFilter:
    """
    TagLeafを統合してTagSetに変換するフィルター
    
    設計書4.5 ⑤ Filter ステージの実装
    ignore_tags適用、正規化処理をサポート
    """
    
    def __init__(self, context: ResolverContext):
        self.context = context
    
    def filter_ast(self, ast: TemplateAST) -> OrderedSet[str]:
        """
        AST内のTagLeafを統合しTagSetに変換
        
        Args:
            ast: 入力AST（TagLeaf混在）
            
        Returns:
            統合・フィルタリング済みTagSet
            
        Raises:
            TagFilterError: 重大なエラー時（strict_level="error"）
        """
        try:
            # TagLeafノードからタグを収集
            collected_tags = self._collect_tagset_from_ast(ast)
            
            # ignore_tags適用
            filtered_tags = self._apply_ignore_tags(collected_tags)
            
            return filtered_tags
            
        except Exception as e:
            # 予期しないエラーの処理
            logger.error(f"Unexpected error in TagFilter: {e}")
            if self.context.strict_level == "error":
                raise TagFilterError(f"Failed to filter AST: {e}")
            else:
                # warn/softの場合は空のTagSetを返す
                if self.context.strict_level == "warn":
                    logger.warning(f"TagFilter error, returning empty TagSet: {e}")
                return OrderedSet()
    
    def _collect_tagset_from_ast(self, ast: TemplateAST) -> OrderedSet[str]:
        """
        TagLeafノードからタグを収集
        
        Args:
            ast: 入力AST
            
        Returns:
            TagLeafから収集されたタグセット
        """
        result = OrderedSet()
        
        for node in ast:
            if isinstance(node, TagLeaf):
                # TagLeaf.tagsをOrderedSetに統合
                result.update(node.tags)
            elif isinstance(node, Text):
                # Textノードは分割せず、そのまま単一要素として追加
                result.add(node.value)
            # その他のノードは無視
        
        return result
    
    
    def _normalize_tag(self, tag: str) -> str:
        """
        タグ正規化（既存実装準拠: strip().lower()）
        
        Args:
            tag: 正規化対象タグ
            
        Returns:
            正規化済みタグ
        """
        return tag.strip().lower()
    
    def _apply_ignore_tags(self, tags: OrderedSet[str]) -> OrderedSet[str]:
        """
        ignore_tags適用（正規化比較）
        
        Args:
            tags: フィルタリング対象TagSet
            
        Returns:
            ignore_tags適用後のTagSet
        """
        result = OrderedSet()
        
        for tag in tags:
            if not self.context.should_ignore_tag(tag):
                result.add(tag)
            elif self.context.strict_level in ("warn", "error"):
                # warnとerrorレベルでは情報提供としてログ出力
                logger.warning(f"Tag '{tag}' ignored by ignore_tags")
        
        return result