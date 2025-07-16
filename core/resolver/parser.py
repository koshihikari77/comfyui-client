"""
PromptResolver V2 TemplateParser実装

設計書4.1および10.2に基づく実装
"""

from typing import List, Optional, Dict, Any
from pathlib import Path
from lark import Lark, Transformer, Tree, Token
from lark.exceptions import LarkError
import logging
import hashlib
import threading

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
            raise RecursionLimitError(f"Template parsing depth exceeded {MAX_DEPTH}", depth=self.depth)
    
    def _enter_depth(self):
        """再帰深度に入る際の処理"""
        self.depth += 1
        self._check_depth()
    
    def _exit_depth(self):
        """再帰深度から出る際の処理"""
        self.depth -= 1
    
    def template(self, nodes: List[ASTNode]) -> TemplateAST:
        """テンプレート全体を処理"""
        # templateは最上位なので、深度をリセット
        self.depth = 0
        self._enter_depth()
        try:
            # Noneや空要素を除去
            return [node for node in nodes if node is not None]
        finally:
            self._exit_depth()
    
    def text(self, tokens: List[Token]) -> Text:
        """テキストノードを作成"""
        self._enter_depth()
        try:
            # 複数のTEXTトークンを連結
            value = "".join(str(token) for token in tokens)
            # エスケープ処理
            value = self._unescape_text(value)
            return Text(value=value)
        finally:
            self._exit_depth()
    
    def preset(self, children: List) -> PresetExpr:
        """プリセット式ノードを作成"""
        self._enter_depth()
        try:
            # key_expr は children[0] に含まれる
            key_expr = str(children[0])
            return PresetExpr(key_expr=key_expr)
        finally:
            self._exit_depth()
    
    def placeholder(self, children: List[Token]) -> Placeholder:
        """プレースホルダーノードを作成"""
        self._enter_depth()
        try:
            name = str(children[0])
            return Placeholder(name=name)
        finally:
            self._exit_depth()
    
    def wildcard(self, children: List[Token]) -> Wildcard:
        """ワイルドカードノードを作成"""
        self._enter_depth()
        try:
            # 新しい文法: WILDCARDは1つのトークンとして認識される
            # __name__形式から前後の__を除去
            token_value = str(children[0])
            key = token_value[2:-2]  # 前後の__を除去
            return Wildcard(key=key)
        finally:
            self._exit_depth()
    
    def key_expr(self, children: List) -> str:
        """キー式を文字列として結合"""
        self._enter_depth()
        try:
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
        finally:
            self._exit_depth()
    
    def operator(self, children: List) -> str:
        """演算子を文字列として返す"""
        self._enter_depth()
        try:
            if len(children) > 0:
                return str(children[0])
            else:
                return ""
        finally:
            self._exit_depth()
    
    def group(self, children: List[Token]) -> str:
        """グループ（name#subgroup形式）を文字列として結合"""
        self._enter_depth()
        try:
            if len(children) == 1:
                return str(children[0])
            elif len(children) == 2:
                return f"{children[0]}#{children[1]}"
            else:
                return str(children[0])
        finally:
            self._exit_depth()
    
    def _unescape_text(self, text: str) -> str:
        """エスケープされた文字を元に戻す"""
        # 設計書10.1のエスケープ処理
        text = text.replace("\\<", "<")
        text = text.replace("\\{", "{")
        text = text.replace("\\__", "__")
        return text


class TemplateParser:
    """テンプレート文字列をASTに変換するパーサー"""
    
    # クラス変数でLarkインスタンスをキャッシュ
    _parser_cache: Dict[str, Lark] = {}
    _cache_lock = threading.Lock()
    
    def __init__(self):
        # 文法ファイルのパス
        grammar_path = Path(__file__).parent / "template.lark"
        
        try:
            with open(grammar_path, 'r', encoding='utf-8') as f:
                grammar = f.read()
            
            # grammar contentのハッシュをキーとしてキャッシュ
            grammar_hash = hashlib.md5(grammar.encode('utf-8')).hexdigest()
            
            with self._cache_lock:
                if grammar_hash not in self._parser_cache:
                    # Transformerは指定せず、Larkインスタンスのみキャッシュ
                    self._parser_cache[grammar_hash] = Lark(
                        grammar,
                        parser='lalr',
                        debug=False
                    )
                    logger.info(f"Created new Lark parser for grammar hash: {grammar_hash[:8]}")
                else:
                    logger.debug(f"Reusing cached Lark parser for grammar hash: {grammar_hash[:8]}")
                
                self.parser = self._parser_cache[grammar_hash]
            
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
            # Larkで解析（Transformerなし）
            tree = self.parser.parse(template)
            
            # 動的にTransformerを適用してASTに変換
            transformer = TemplateTransformer()
            ast = transformer.transform(tree)
            
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
            # Larkの解析エラーをParseErrorに変換（位置情報付き）
            line = getattr(e, 'line', -1)
            column = getattr(e, 'column', -1)
            position = getattr(e, 'pos_in_stream', -1)
            raise ParseError(
                f"Template parsing failed: {e}", 
                template, 
                position=position, 
                line=line, 
                column=column
            )
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