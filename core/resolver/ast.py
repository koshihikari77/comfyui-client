"""
PromptResolver V2 AST ノード定義

設計書3.3に基づくAST(Abstract Syntax Tree)ノード定義
"""

from typing import Dict, Any, List, Union
from pydantic import BaseModel
from ordered_set import OrderedSet


class Node(BaseModel):
    """AST ノードの基底クラス"""
    pass


class Text(Node):
    """プレーンテキストノード"""
    value: str


class PresetExpr(Node):
    """プリセット式ノード"""
    key_expr: str  # "quality#default+hdr" 等


class Placeholder(Node):
    """プレースホルダーノード"""
    name: str
    mode: str = "expand"  # "expand" (直積) | "sample" (ランダム :r)


class Wildcard(Node):
    """ワイルドカードノード"""
    key: str


class TagLeaf(Node):
    """タグセットを保持するリーフノード（プリセット展開後）"""
    tags: OrderedSet[str]
    
    class Config:
        arbitrary_types_allowed = True


# AST の型定義
ASTNode = Union[Text, PresetExpr, Placeholder, Wildcard, TagLeaf]
TemplateAST = List[ASTNode]


def ast_to_dict(node: ASTNode) -> Dict[str, Any]:
    """ASTノードを辞書形式に変換（デバッグ用）"""
    result = {"type": node.__class__.__name__}
    
    if isinstance(node, Text):
        result["value"] = node.value
    elif isinstance(node, PresetExpr):
        result["key_expr"] = node.key_expr
    elif isinstance(node, Placeholder):
        result["name"] = node.name
    elif isinstance(node, Wildcard):
        result["key"] = node.key
    elif isinstance(node, TagLeaf):
        result["tags"] = list(node.tags)
    
    return result


def ast_list_to_dict(ast: TemplateAST) -> List[Dict[str, Any]]:
    """AST全体を辞書形式に変換（デバッグ用）"""
    return [ast_to_dict(node) for node in ast]