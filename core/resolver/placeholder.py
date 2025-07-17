"""
PromptResolver V2 PlaceholderSubstitutor実装

設計書4.3に基づくPlaceholder → Text変換機能
o3アドバイスを反映したexpand/sampleモード実装
"""

import logging
import re
from typing import List, Literal, Union, Dict
from itertools import product, islice
from copy import deepcopy

from .ast import TemplateAST, ASTNode, Placeholder, Text
from .context import ResolverContext
from .exceptions import PlaceholderError, RecursionLimitError

logger = logging.getLogger(__name__)

# 設計書10.2および o3推奨の展開数制限
MAX_EXPANSION = 128

# 設計書10.2に基づく再帰深度制限（parser.pyと同じ値）
MAX_DEPTH = 20


class PlaceholderSubstitutor:
    """
    PlaceholderをTextに置換するサブスティチューター
    
    設計書4.3 ③ Placeholder ステージの実装
    expandモード（直積展開）とsampleモード（ランダム選択）をサポート
    """
    
    def __init__(self, context: ResolverContext, mode: Literal["expand", "sample"] = "sample"):
        self.context = context
        self.mode = mode
        # o3推奨: Parserキャッシュでパフォーマンス最適化
        self._parse_cache: Dict[str, TemplateAST] = {}
        
    def substitute_ast(self, ast: TemplateAST) -> Union[TemplateAST, List[TemplateAST]]:
        """
        ASTを走査してPlaceholderをTextに置換
        
        Args:
            ast: 入力AST
            
        Returns:
            sampleモード: 単一AST
            expandモード: AST のリスト（直積展開）
        """
        # Placeholderノードをインデックスとともに収集
        placeholders = [(i, node) for i, node in enumerate(ast) if isinstance(node, Placeholder)]
        
        if not placeholders:
            # Placeholderが無い場合はそのまま返す
            return ast if self.mode == "sample" else [ast]
        
        if self.mode == "sample":
            return self._substitute_sample(ast, placeholders)
        else:  # expand
            return self._substitute_expand(ast, placeholders)
    
    def _substitute_sample(self, ast: TemplateAST, placeholders: List[tuple]) -> TemplateAST:
        """
        サンプルモード: 各プレースホルダーからランダムに1値を選択
        
        Args:
            ast: 入力AST
            placeholders: [(index, Placeholder), ...] のリスト
            
        Returns:
            Placeholder → Text置換済みAST
        """
        result_ast = deepcopy(ast)
        
        # 後ろから処理してインデックスずれを回避
        for idx, node in reversed(placeholders):
            try:
                candidates = self._get_placeholder_candidates(node.name)
                if not candidates:
                    # 空の場合はエラーハンドリング
                    replacement = self._handle_empty_placeholder(node.name)
                    result_ast[idx] = replacement
                else:
                    choice = self.context.rng.choice(candidates)
                    
                    # o3提案: 再パース機能（多段ネスト対応）
                    if self._needs_reparse(choice):
                        try:
                            # 多段再パース対応: while収束まで継続
                            sub_ast = self._parse_and_evaluate_recursive(choice)
                            # ASTスプライス: 単一ノードを複数ノードで置換
                            result_ast[idx:idx+1] = deepcopy(sub_ast)
                        except Exception as e:
                            # 再パース失敗時のフォールバック
                            logger.warning(f"Reparse failed for placeholder '{node.name}' with choice '{choice}': {e}")
                            if self.context.strict_level == "error":
                                raise
                            result_ast[idx] = Text(value=choice)
                    else:
                        result_ast[idx] = Text(value=choice)
                
            except PlaceholderError as e:
                if self.context.strict_level == "error":
                    raise
                elif self.context.strict_level == "warn":
                    logger.warning(f"PlaceholderError (fallback=empty): {e} | strict_level={self.context.strict_level}")
                    result_ast[idx] = Text(value="")
                else:  # soft
                    result_ast[idx] = Text(value="")
        
        return result_ast
    
    def _substitute_expand(self, ast: TemplateAST, placeholders: List[tuple]) -> List[TemplateAST]:
        """
        展開モード: 全プレースホルダーの直積展開
        
        Args:
            ast: 入力AST
            placeholders: [(index, Placeholder), ...] のリスト
            
        Returns:
            すべての組み合わせのASTリスト
        """
        # 各プレースホルダーの候補リストを取得
        candidate_lists = []
        for idx, node in placeholders:
            try:
                candidates = self._get_placeholder_candidates(node.name)
                if not candidates:
                    candidates = self._handle_empty_placeholder_expand(node.name)
                candidate_lists.append(candidates)
            except PlaceholderError as e:
                if self.context.strict_level == "error":
                    raise
                elif self.context.strict_level == "warn":
                    logger.warning(f"PlaceholderError (fallback=empty): {e} | strict_level={self.context.strict_level}")
                    candidate_lists.append([""])
                else:  # soft
                    candidate_lists.append([""])
        
        # 直積展開（o3推奨：isliceでメモリ安全化改善版）
        product_iter = product(*candidate_lists)
        
        # 各組み合わせごとにAST生成（メモリ効率版）
        result_asts = []
        combo_count = 0
        
        for combo in product_iter:
            combo_count += 1
            
            # 展開数制限チェック（129件目で中断）
            if combo_count > MAX_EXPANSION:
                raise RecursionLimitError(
                    f"Placeholder expansion too large: >{MAX_EXPANSION} combinations",
                    depth=combo_count
                )
            cloned_ast = deepcopy(ast)
            
            # 後ろから処理してインデックスずれを回避
            for (idx, node), value in reversed(list(zip(placeholders, combo))):
                # o3提案: 再パース機能（多段ネスト対応）
                if self._needs_reparse(value):
                    try:
                        # 多段再パース対応: while収束まで継続
                        sub_ast = self._parse_and_evaluate_recursive(value)
                        # ASTスプライス: 単一ノードを複数ノードで置換
                        cloned_ast[idx:idx+1] = deepcopy(sub_ast)
                    except Exception as e:
                        # 再パース失敗時のフォールバック
                        logger.warning(f"Reparse failed for placeholder '{node.name}' with value '{value}': {e}")
                        if self.context.strict_level == "error":
                            raise
                        cloned_ast[idx] = Text(value=value)
                else:
                    cloned_ast[idx] = Text(value=value)
            
            result_asts.append(cloned_ast)
        
        return result_asts
    
    def _get_placeholder_candidates(self, name: str) -> List[str]:
        """
        プレースホルダー名から候補リストを取得
        
        Args:
            name: プレースホルダー名
            
        Returns:
            候補文字列のリスト
            
        Raises:
            PlaceholderError: プレースホルダーが未定義の場合
        """
        if name not in self.context.placeholders:
            raise PlaceholderError(f"Placeholder '{name}' not found", placeholder_name=name)
        
        candidates = self.context.placeholders[name]
        if not isinstance(candidates, list):
            raise PlaceholderError(f"Placeholder '{name}' must be a list, got {type(candidates)}", placeholder_name=name)
        
        return candidates
    
    def _handle_empty_placeholder(self, name: str) -> Text:
        """
        空のプレースホルダーハンドリング（sampleモード）
        
        Args:
            name: プレースホルダー名
            
        Returns:
            空文字のTextノード
        """
        if self.context.strict_level == "error":
            raise PlaceholderError(f"Placeholder '{name}' has empty candidates", placeholder_name=name)
        elif self.context.strict_level == "warn":
            logger.warning(f"Placeholder '{name}' has empty candidates (fallback=empty) | strict_level={self.context.strict_level}")
        
        return Text(value="")
    
    def _handle_empty_placeholder_expand(self, name: str) -> List[str]:
        """
        空のプレースホルダーハンドリング（expandモード）
        
        Args:
            name: プレースホルダー名
            
        Returns:
            空文字を含むリスト
        """
        if self.context.strict_level == "error":
            raise PlaceholderError(f"Placeholder '{name}' has empty candidates", placeholder_name=name)
        elif self.context.strict_level == "warn":
            logger.warning(f"Placeholder '{name}' has empty candidates (fallback=empty) | strict_level={self.context.strict_level}")
        
        return [""]
    
    def _needs_reparse(self, choice: str) -> bool:
        """
        再パースが必要かどうかを判定（o3推奨：正規表現で厳密化）
        
        Args:
            choice: 置換候補文字列
            
        Returns:
            テンプレート構文が含まれている場合True
        """
        # Preset構文: <preset:xxx> （改善：preset:を厳密チェック）
        if re.search(r'<preset:[A-Za-z0-9_#+-]+>', choice):
            return True
        # Placeholder構文: {xxx} （改善：内容を厳密チェック）
        if re.search(r'\{[A-Za-z0-9_]+\}', choice):
            return True
        # Wildcard構文: __xxx__ （改善：完全一致チェック）
        if re.fullmatch(r'__[A-Za-z0-9_-]+__', choice):
            return True
        return False
    
    def _parse_and_evaluate(self, choice: str) -> TemplateAST:
        """
        文字列を再パースしてAST化（o3提案）
        
        Args:
            choice: 再パース対象文字列
            
        Returns:
            パース・評価済みのAST
            
        Raises:
            ParseError: パースに失敗した場合
            RecursionLimitError: 再帰深度超過の場合
        """
        # 循環importを避けるため、遅延import
        from .parser import TemplateParser
        from .preset import PresetEvaluator
        
        try:
            # 再帰深度管理（o3推奨：context共有カウンタ使用）
            self.context.reparse_depth += 1
            if self.context.reparse_depth > MAX_DEPTH:
                raise RecursionLimitError(
                    f"Placeholder reparse depth exceeded {MAX_DEPTH}",
                    depth=self.context.reparse_depth
                )
            
            # TemplateParserでパース（o3推奨: キャッシュ使用）
            sub_ast = self._parse_with_cache(choice)
            
            # PresetEvaluatorで評価（プリセット展開）
            evaluator = PresetEvaluator(self.context)
            evaluated_ast = evaluator.evaluate_ast(sub_ast)
            
            return evaluated_ast
            
        finally:
            # 例外が発生してもdepthをデクリメント
            self.context.reparse_depth -= 1
    
    def _parse_with_cache(self, choice: str) -> TemplateAST:
        """
        文字列をキャッシュ付きでパース（o3推奨パフォーマンス最適化）
        
        Args:
            choice: パース対象文字列
            
        Returns:
            パース済みAST
        """
        if choice in self._parse_cache:
            # キャッシュヒット: deepcopyして返す（ASTの独立性確保）
            return deepcopy(self._parse_cache[choice])
        
        # キャッシュミス: パース実行
        from .parser import TemplateParser
        parser = TemplateParser()
        sub_ast = parser.parse(choice)
        
        # キャッシュに保存（LRUライクに制限）
        if len(self._parse_cache) >= 50:  # 最大50エントリ
            # 最古のエントリを削除
            oldest_key = next(iter(self._parse_cache))
            del self._parse_cache[oldest_key]
        
        self._parse_cache[choice] = deepcopy(sub_ast)
        return sub_ast
    
    def _parse_and_evaluate_recursive(self, choice: str) -> TemplateAST:
        """
        多段ネスト対応: while再帰で完全展開（o3推奨改善版）
        
        Args:
            choice: 再パース対象文字列
            
        Returns:
            完全に展開されたAST
            
        Raises:
            RecursionLimitError: 再帰深度超過の場合
        """
        current_ast = [Text(value=choice)]
        max_iterations = 15  # 無限ループ防止（多段対応で増加）
        iteration = 0
        
        while iteration < max_iterations:
            # AST内に再パース対象があるかチェック
            needs_further_reparse = False
            new_ast = []
            
            for node in current_ast:
                if isinstance(node, Text) and self._needs_reparse(node.value):
                    needs_further_reparse = True
                    try:
                        # Text内のテンプレート構文を再パース
                        sub_ast = self._parse_and_evaluate(node.value)
                        new_ast.extend(sub_ast)
                    except Exception as e:
                        logger.warning(f"Multi-stage reparse failed at iteration {iteration}: {e}")
                        new_ast.append(node)  # 失敗時は元のTextを保持
                else:
                    # 再パース不要または非Textノード
                    new_ast.append(node)
            
            # 再パース対象が無くなったら終了
            if not needs_further_reparse:
                return new_ast
            
            current_ast = new_ast
            iteration += 1
        
        # 最大イテレーション到達時の警告
        logger.warning(f"Multi-stage reparse reached max iterations ({max_iterations}), stopping")
        return current_ast