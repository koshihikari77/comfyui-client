"""
PromptResolver V2 ResolverContext定義

設計書3.2に基づくResolverContextクラス定義
"""

from typing import Dict, List, Set, Any, Literal, Optional
from random import Random
from pydantic import BaseModel, field_validator, model_validator
import re
import logging

logger = logging.getLogger(__name__)


class PresetFile(BaseModel):
    """
    プリセットファイルモデル
    
    設計書3.4に基づく実装
    """
    version: Literal[1, 2] = 2  # 無指定なら v2 扱い
    description: Optional[str] = None
    metadata: Dict[str, Any] = {}
    contents: Dict[str, Any]  # 正規化後（V2形式ネスト構造対応）
    
    @field_validator("contents", mode="before")
    @classmethod
    def normalize_contents(cls, v):
        """list / 文字列を list[str] へ、カンマ・読点 split"""
        if isinstance(v, list):
            # V1形式の場合（ルートがlist）
            return {"__all__": v}
        
        out = {}
        for k, val in v.items():
            # キーを文字列に変換（数値キー対応）
            str_key = str(k)
            
            if isinstance(val, str):
                # 文字列の場合はカンマ・読点で分割
                parts = re.split(r"[,、]", val)
                out[str_key] = [p.strip() for p in parts if p.strip()]
            elif isinstance(val, list):
                # リストの場合はそのまま
                out[str_key] = val
            elif isinstance(val, dict):
                # V2形式ネスト構造の場合：辞書のまま保持
                out[str_key] = val
            else:
                # その他の場合は空リスト
                out[k] = []
        return out
    
    @model_validator(mode="before")
    @classmethod
    def set_version_from_format(cls, values):
        """V1形式検出時にversionを自動設定"""
        if isinstance(values, dict):
            # contentsがV1形式（list）の場合、versionを1に設定
            contents = values.get("contents")
            if isinstance(contents, list) and "version" not in values:
                values["version"] = 1
                logger.info("Detected V1 preset format, setting version=1")
        return values


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
    # Placeholder/Wildcard 再パース時の深度カウンタ（全ステージ共有）
    reparse_depth: int = 0
    # 直積展開の上限（超えると RecursionLimitError）。設定で上書き可能。
    placeholder_max_expansion: int = 128
    
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
            strict_level="warn",
            reparse_depth=0,
            placeholder_max_expansion=128,
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
    
    def reset_reparse_depth(self) -> None:
        """再パース深度カウンタをリセット（Phase4推奨：安全性向上）"""
        self.reparse_depth = 0
