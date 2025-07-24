"""
PromptResolver V2 PromptFormatter実装

設計書4.6に基づくTagSet → String変換機能
locale対応、オプション機能をサポート
"""

import logging
from typing import List
from ordered_set import OrderedSet

from .context import ResolverContext
from .exceptions import PromptFormatterError

logger = logging.getLogger(__name__)


class PromptFormatter:
    """
    TagSetを最終プロンプト文字列に変換するフォーマッター
    
    設計書4.6 ⑥ Format ステージの実装
    locale対応、オプション機能をサポート
    """
    
    def __init__(self, context: ResolverContext):
        self.context = context
    
    def format_tagset(self, tagset: OrderedSet[str]) -> str:
        """
        TagSetを最終プロンプト文字列に変換
        
        Args:
            tagset: 入力TagSet（OrderedSet[str]）
            
        Returns:
            最終プロンプト文字列
            
        Raises:
            PromptFormatterError: 重大なエラー時（strict_level="error"）
        """
        try:
            # OrderedSet → List変換
            tags = self._tagset_to_list(tagset)
            
            # フォーマッティングオプション適用（将来拡張用）
            tags = self._apply_formatting_options(tags)
            
            # locale区切り文字でjoin
            result = self._join_with_locale(tags)
            
            return result
            
        except Exception as e:
            # 予期しないエラーの処理
            logger.error(f"Unexpected error in PromptFormatter: {e}")
            if self.context.strict_level == "error":
                raise PromptFormatterError(f"Failed to format TagSet: {e}", tagset_length=len(tagset))
            else:
                # warn/softの場合は空文字列を返す
                if self.context.strict_level == "warn":
                    logger.warning(f"PromptFormatter error, returning empty string: {e}")
                return ""
    
    def _tagset_to_list(self, tagset: OrderedSet[str]) -> List[str]:
        """
        OrderedSet → List変換
        
        Args:
            tagset: 変換対象OrderedSet
            
        Returns:
            List形式のタグリスト
        """
        return list(tagset)
    
    def _apply_formatting_options(self, tags: List[str]) -> List[str]:
        """
        フォーマッティングオプション適用（将来拡張用）
        
        Args:
            tags: 処理対象タグリスト
            
        Returns:
            オプション適用後のタグリスト
        """
        result = tags[:]  # コピーを作成
        
        # 将来拡張: sort_alpha機能
        # if hasattr(self.context, 'sort_alpha') and self.context.sort_alpha:
        #     result = self._apply_sort_alpha(result)
        
        # 将来拡張: shuffle機能  
        # if hasattr(self.context, 'shuffle') and self.context.shuffle:
        #     result = self._apply_shuffle(result)
        
        return result
    
    def _apply_sort_alpha(self, tags: List[str]) -> List[str]:
        """
        アルファベット順ソート適用（将来拡張用）
        
        Args:
            tags: ソート対象タグリスト
            
        Returns:
            ソート済みタグリスト
        """
        return sorted(tags, key=str.lower)
    
    def _apply_shuffle(self, tags: List[str]) -> List[str]:
        """
        シャッフル適用（将来拡張用）
        
        Args:
            tags: シャッフル対象タグリスト
            
        Returns:
            シャッフル済みタグリスト
        """
        shuffled = tags[:]
        self.context.rng.shuffle(shuffled)
        return shuffled
    
    def _join_with_locale(self, tags: List[str]) -> str:
        """
        locale区切り文字でjoin（パターン判定結合）
        
        Args:
            tags: 結合対象タグリスト
            
        Returns:
            locale区切りで結合された文字列
        """
        # 空リストは空文字列
        if not tags:
            return ""
        
        # 単一タグは区切り文字なし
        if len(tags) == 1:
            return tags[0]
        
        # パターン判定結合
        result_parts = [tags[0]]  # 最初の要素
        
        for i, tag in enumerate(tags[1:], 1):
            prev_tag = tags[i-1]
            
            # 先頭パターン判定（スペース・カンマ開始）
            if tag.startswith(' ') or tag.startswith(','):
                result_parts.append(tag)  # 直結合
            # 末尾パターン判定（前要素が末尾スペース・カンマ）
            elif prev_tag.endswith(' ') or prev_tag.endswith(','):
                result_parts.append(tag)  # 直結合
            else:  # 通常要素→カンマ区切り
                delimiter = self._validate_locale()
                result_parts.append(delimiter + tag)
        
        return ''.join(result_parts)
    
    def _validate_locale(self) -> str:
        """
        locale値の妥当性検証
        
        Returns:
            使用する区切り文字（フォールバック含む）
        """
        # locale → 実際の区切り文字のマッピング
        locale_mapping = {
            ",": ", ",    # カンマ+スペース（V1互換）
            "、": "、",    # 全角読点
            ";": ";"      # セミコロン
        }
        
        if self.context.locale not in locale_mapping:
            if self.context.strict_level == "error":
                raise PromptFormatterError(f"Unsupported locale: {self.context.locale}")
            elif self.context.strict_level == "warn":
                logger.warning(f"Unsupported locale '{self.context.locale}', using ',' as fallback")
            return ", "  # フォールバック（カンマ+スペース）
        
        return locale_mapping[self.context.locale]