"""
PromptResolver V2 WildcardSubstitutor実装

設計書4.4に基づくWildcard → Text変換機能
PlaceholderSubstitutorパターンを参考にしたsampleモード実装
再パース機能付きで高度なテンプレート構文をサポート
"""

import logging
import re
from typing import List, Dict
from copy import deepcopy

from .ast import TemplateAST, ASTNode, Wildcard, Text
from .context import ResolverContext
from .exceptions import WildcardError, RecursionLimitError

logger = logging.getLogger(__name__)

# 設計書10.2に基づく再帰深度制限（placeholder.pyと同じ値）
MAX_DEPTH = 20


class WildcardSubstitutor:
    """
    WildcardをTextに置換するサブスティチューター
    
    設計書4.4 ④ Wildcard ステージの実装
    sampleモード（ランダム選択）のみをサポート
    Wildcardはランダム要素の注入が目的のため、expandモードは不要
    """
    
    def __init__(self, context: ResolverContext):
        self.context = context
        # 再パース機能: Parserキャッシュでパフォーマンス最適化
        self._parse_cache: Dict[str, TemplateAST] = {}
        
    def substitute_ast(self, ast: TemplateAST) -> TemplateAST:
        """
        ASTを走査してWildcardをTextに置換
        
        Args:
            ast: 入力AST
            
        Returns:
            Wildcard → Text置換済みAST
        """
        # Wildcardノードをインデックスとともに収集
        wildcards = [(i, node) for i, node in enumerate(ast) if isinstance(node, Wildcard)]
        
        if not wildcards:
            # Wildcardが無い場合はそのまま返す
            return ast
        
        return self._substitute_sample(ast, wildcards)
    
    def _substitute_sample(self, ast: TemplateAST, wildcards: List[tuple]) -> TemplateAST:
        """
        サンプルモード: 各ワイルドカードからランダムに1値を選択
        
        Args:
            ast: 入力AST
            wildcards: [(index, Wildcard), ...] のリスト
            
        Returns:
            Wildcard → Text置換済みAST
        """
        result_ast = deepcopy(ast)
        
        # 後ろから処理してインデックスずれを回避
        for idx, node in reversed(wildcards):
            try:
                candidates = self._get_wildcard_candidates(node.key)
                if not candidates:
                    # 空の場合はエラーハンドリング
                    replacement = self._handle_empty_wildcard(node.key)
                    result_ast[idx] = replacement
                else:
                    choice = self.context.rng.choice(candidates)
                    
                    # 再パース機能: choice内にテンプレート構文が含まれる場合
                    # ただし、フォールバック文字列（__key__形式）は再パースしない
                    if self._needs_reparse(choice) and not self._is_fallback_wildcard(choice):
                        try:
                            # 多段再パース対応: while収束まで継続
                            sub_ast = self._parse_and_evaluate_recursive(choice)
                            # ASTスプライス: 単一ノードを複数ノードで置換
                            result_ast[idx:idx+1] = deepcopy(sub_ast)
                        except Exception as e:
                            # 再パース失敗時のフォールバック
                            logger.warning(f"Reparse failed for wildcard '{node.key}' with choice '{choice}': {e}")
                            if self.context.strict_level == "error":
                                raise
                            result_ast[idx] = Text(value=choice)
                    else:
                        result_ast[idx] = Text(value=choice)
                    
            except Exception as e:
                # 予期しないエラーの処理
                logger.error(f"Unexpected error substituting wildcard '{node.key}': {e}")
                if self.context.strict_level == "error":
                    raise WildcardError(f"Failed to substitute wildcard '{node.key}': {e}", wildcard_key=node.key)
                else:
                    # フォールバック: 元のWildcard形式で返す
                    result_ast[idx] = Text(value=f"__{node.key}__")
        
        return result_ast
    
    def _get_wildcard_candidates(self, key: str) -> List[str]:
        """
        ワイルドカードキーに対応する候補リストを取得
        
        Args:
            key: ワイルドカードキー
            
        Returns:
            候補文字列のリスト
            
        Raises:
            WildcardError: ワイルドカードが未定義の場合
        """
        if key not in self.context.wildcards:
            message = f"Wildcard '{key}' is not defined"
            if self.context.strict_level == "error":
                raise WildcardError(message, wildcard_key=key)
            elif self.context.strict_level == "warn":
                logger.warning(message)
                # 未定義の場合はフォールバック文字列を返す
                return [f"__{key}__"]
            else:  # soft
                # 未定義の場合はフォールバック文字列を返す
                return [f"__{key}__"]
        
        return self.context.wildcards[key]
    
    def _handle_empty_wildcard(self, key: str) -> Text:
        """
        空のワイルドカード候補に対するエラーハンドリング
        
        Args:
            key: ワイルドカードキー
            
        Returns:
            フォールバック用のTextノード
            
        Raises:
            WildcardError: strict_level="error"の場合
        """
        message = f"Wildcard '{key}' has no candidates"
        
        if self.context.strict_level == "error":
            raise WildcardError(message, wildcard_key=key)
        elif self.context.strict_level == "warn":
            logger.warning(message)
            return Text(value="")  # 空文字列で置換
        else:  # soft
            return Text(value="")  # 空文字列で置換
    
    def _needs_reparse(self, choice: str) -> bool:
        """
        再パースが必要かどうかを判定（PlaceholderSubstitutorと同様）
        
        Args:
            choice: 置換候補文字列
            
        Returns:
            テンプレート構文が含まれている場合True
        """
        # Preset構文: <preset:xxx> （/を含むキーに対応、Phase 5改善）
        if re.search(r'<preset:[A-Za-z0-9_#+\-/]+>', choice):
            return True
        # Placeholder構文: {xxx} （改善：内容を厳密チェック）
        if re.search(r'\{[A-Za-z0-9_]+\}', choice):
            return True
        # Wildcard構文: __xxx__ （/を含むキーに対応、Phase 5改善）
        if re.search(r'__[A-Za-z0-9_\-/]+__', choice):
            return True
        return False
    
    def _is_fallback_wildcard(self, choice: str) -> bool:
        """
        フォールバック文字列（__key__形式）かどうかを判定
        
        Args:
            choice: 判定対象文字列
            
        Returns:
            フォールバック文字列の場合True
        """
        # __key__形式で、前後に他の文字が無い場合のみフォールバック文字列とみなす
        return re.match(r'^__[A-Za-z0-9_-]+__$', choice) is not None
    
    def _parse_and_evaluate_recursive(self, choice: str) -> TemplateAST:
        """
        多段ネスト対応: while再帰で完全展開（PlaceholderSubstitutorと同様）
        
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
    
    def _parse_and_evaluate(self, choice: str) -> TemplateAST:
        """
        文字列を再パースしてAST化（PlaceholderSubstitutorと同様）
        
        Args:
            choice: 再パース対象文字列
            
        Returns:
            パース・評価済みAST
            
        Raises:
            RecursionLimitError: 再帰深度超過の場合
        """
        try:
            # 再帰深度管理（共有カウンタ使用）
            self.context.reparse_depth += 1
            if self.context.reparse_depth > MAX_DEPTH:
                raise RecursionLimitError(
                    f"Wildcard reparse depth exceeded {MAX_DEPTH}",
                    depth=self.context.reparse_depth
                )
            
            # TemplateParserでパース（キャッシュ使用）
            sub_ast = self._parse_with_cache(choice)
            
            # PresetEvaluatorで評価（プリセット展開）
            from .preset import PresetEvaluator
            evaluator = PresetEvaluator(self.context)
            evaluated_ast = evaluator.evaluate_ast(sub_ast)
            
            return evaluated_ast
            
        finally:
            # 例外が発生してもdepthをデクリメント
            self.context.reparse_depth -= 1
    
    def _parse_with_cache(self, choice: str) -> TemplateAST:
        """
        文字列をキャッシュ付きでパース（PlaceholderSubstitutorと同様）
        
        Args:
            choice: パース対象文字列
            
        Returns:
            パース済みAST
        """
        if choice in self._parse_cache:
            # キャッシュヒット: deepcopyして返す（AST独立性確保）
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