"""
PromptResolver V2 TemplateParser実装

設計書4.1および10.2に基づく実装
"""

from typing import List, Optional
from pathlib import Path
from lark import Lark, Transformer, Tree, Token
from lark.exceptions import LarkError
import logging

from .ast import TemplateAST, ASTNode, Text, PresetExpr, Placeholder, Wildcard
from .exceptions import ParseError, RecursionLimitError

logger = logging.getLogger(__name__)

# 設計書10.2に基づく再帰深度制限
MAX_DEPTH = 20


class TemplateTransformer(Transformer):
    """Lark解析結果をASTノードに変換するTransformer"""
    
    def __init__(self):
        super().__init__()
        self.depth = 0
    
    def _check_depth(self):
        """再帰深度チェック"""
        if self.depth > MAX_DEPTH:
            raise RecursionLimitError(f"Template parsing depth exceeded {MAX_DEPTH}")
    
    def template(self, nodes: List[ASTNode]) -> TemplateAST:
        """テンプレート全体を処理"""
        self._check_depth()
        # Noneや空要素を除去
        return [node for node in nodes if node is not None]
    
    def text(self, tokens: List[Token]) -> Text:
        """テキストノードを作成"""
        self._check_depth()
        # 複数のTEXTトークンを連結
        value = "".join(str(token) for token in tokens)
        # エスケープ処理
        value = self._unescape_text(value)
        return Text(value=value)
    
    def preset(self, children: List) -> PresetExpr:
        """プリセット式ノードを作成"""
        self._check_depth()
        # key_expr は children[0] に含まれる
        key_expr = str(children[0])
        return PresetExpr(key_expr=key_expr)
    
    def placeholder(self, children: List[Token]) -> Placeholder:
        """プレースホルダーノードを作成"""
        self._check_depth()
        name = str(children[0])
        return Placeholder(name=name)
    
    def wildcard(self, children: List[Token]) -> Wildcard:
        """ワイルドカードノードを作成"""
        self._check_depth()
        # 新しい文法: WILDCARDは1つのトークンとして認識される
        # __name__形式から前後の__を除去
        token_value = str(children[0])
        key = token_value[2:-2]  # 前後の__を除去
        return Wildcard(key=key)
    
    def key_expr(self, children: List) -> str:
        """キー式を文字列として結合"""
        self._check_depth()
        # 最初のgroupと、それに続く演算子+groupの組み合わせ
        result = str(children[0])
        i = 1
        while i < len(children):
            # 演算子（+/-）を追加
            if i < len(children):
                operator = str(children[i])
                result += operator
                i += 1
            
            # 次のgroupがあれば追加
            if i < len(children):
                group = str(children[i])
                result += group
                i += 1
        return result
    
    def operator(self, children: List) -> str:
        """演算子を文字列として返す"""
        self._check_depth()
        if len(children) > 0:
            return str(children[0])
        else:
            return ""
    
    def group(self, children: List[Token]) -> str:
        """グループ（name#subgroup形式）を文字列として結合"""
        self._check_depth()
        if len(children) == 1:
            return str(children[0])
        elif len(children) == 2:
            return f"{children[0]}#{children[1]}"
        else:
            return str(children[0])
    
    def _unescape_text(self, text: str) -> str:
        """エスケープされた文字を元に戻す"""
        # 設計書10.1のエスケープ処理
        text = text.replace("\\<", "<")
        text = text.replace("\\{", "{")
        text = text.replace("\\__", "__")
        return text


class TemplateParser:
    """テンプレート文字列をASTに変換するパーサー"""
    
    def __init__(self):
        # 文法ファイルのパス
        grammar_path = Path(__file__).parent / "template.lark"
        
        try:
            with open(grammar_path, 'r', encoding='utf-8') as f:
                grammar = f.read()
            
            self.parser = Lark(
                grammar,
                parser='lalr',
                transformer=TemplateTransformer(),
                debug=False
            )
            
        except FileNotFoundError:
            raise ParseError(f"Grammar file not found: {grammar_path}")
        except Exception as e:
            raise ParseError(f"Failed to initialize parser: {e}")
    
    def parse(self, template: str) -> TemplateAST:
        """
        テンプレート文字列をASTに変換
        
        Args:
            template: 解析対象のテンプレート文字列
            
        Returns:
            TemplateAST: 解析結果のAST
            
        Raises:
            ParseError: 解析エラーが発生した場合
            RecursionLimitError: 再帰深度制限に達した場合
        """
        if not template:
            return []
        
        try:
            # Larkで解析してASTに変換
            ast = self.parser.parse(template)
            
            # 結果が直接ASTなのでそのまま返す
            if isinstance(ast, list):
                return ast
            else:
                # 単一ノードの場合はリストに包む
                return [ast] if ast else []
                
        except RecursionLimitError:
            # 再帰深度制限エラーはそのまま再発行
            raise
        except LarkError as e:
            # Larkの解析エラーをParseErrorに変換
            raise ParseError(f"Template parsing failed: {e}", template)
        except Exception as e:
            # その他のエラーもParseErrorに変換
            raise ParseError(f"Unexpected error during parsing: {e}", template)
    
    def validate_template(self, template: str) -> bool:
        """
        テンプレート文字列の妥当性をチェック
        
        Args:
            template: チェック対象のテンプレート文字列
            
        Returns:
            bool: 妥当な場合True、そうでなければFalse
        """
        try:
            self.parse(template)
            return True
        except (ParseError, RecursionLimitError):
            return False