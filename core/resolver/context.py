"""
PromptResolver V2 ResolverContext定義

設計書3.2に基づくResolverContextクラス定義
"""

from typing import Dict, List, Set, Any, Literal, Optional
from random import Random
from pydantic import BaseModel, field_validator
import re


class PresetFile(BaseModel):
    """
    プリセットファイルモデル
    
    設計書3.4に基づく実装
    """
    version: Literal[1, 2] = 2  # 無指定なら v2 扱い
    description: Optional[str] = None
    metadata: Dict[str, Any] = {}
    contents: Dict[str, List[str]]  # 正規化後
    
    @field_validator("contents", mode="before")
    @classmethod
    def normalize_contents(cls, v):
        """list / 文字列を list[str] へ、カンマ・読点 split"""
        if isinstance(v, list):
            # V1形式の場合（ルートがlist）
            return {"__all__": v}
        
        out = {}
        for k, val in v.items():
            if isinstance(val, str):
                # 文字列の場合はカンマ・読点で分割
                parts = re.split(r"[,、]", val)
                out[k] = [p.strip() for p in parts if p.strip()]
            elif isinstance(val, list):
                # リストの場合はそのまま
                out[k] = val
            else:
                # その他の場合は空リスト
                out[k] = []
        return out


class ResolverContext(BaseModel):
    """
    Resolver実行コンテキスト
    
    設計書3.2に基づく実装
    各パイプラインステージが参照する共通データ
    """
    presets: Dict[str, PresetFile]
    wildcards: Dict[str, List[str]]
    rng: Random  # 乱数インスタンス
    ignore_tags: Set[str] = set()
    ignore_groups: Set[str] = set()
    placeholders: Dict[str, List[str]] = {}
    locale: Literal[",", "、", ";"] = ","
    strict_level: Literal["soft", "warn", "error"] = "warn"  # エラー扱いポリシー
    
    class Config:
        arbitrary_types_allowed = True
    
    @classmethod
    def create_default(cls) -> "ResolverContext":
        """デフォルトのコンテキストを作成"""
        return cls(
            presets={},
            wildcards={},
            rng=Random(),
            ignore_tags=set(),
            ignore_groups=set(),
            placeholders={},
            locale=",",
            strict_level="warn"
        )
    
    def with_seed(self, seed: int) -> "ResolverContext":
        """指定されたシードで新しいコンテキストを作成"""
        new_rng = Random(seed)
        return self.copy(update={"rng": new_rng})
    
    def with_placeholders(self, placeholders: Dict[str, List[str]]) -> "ResolverContext":
        """指定されたプレースホルダーで新しいコンテキストを作成"""
        return self.copy(update={"placeholders": placeholders})
    
    def should_ignore_tag(self, tag: str) -> bool:
        """タグが無視対象かどうかチェック"""
        normalized_tag = tag.strip().lower()
        return any(
            ignored.strip().lower() == normalized_tag 
            for ignored in self.ignore_tags
        )
    
    def should_ignore_group(self, group: str) -> bool:
        """グループが無視対象かどうかチェック"""
        return group in self.ignore_groups