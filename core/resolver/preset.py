"""
PromptResolver V2 PresetEvaluator実装

設計書4.2に基づくPresetExpr → TagLeaf変換機能
"""

import re
import logging
from typing import List, Optional, Tuple, Dict
from ordered_set import OrderedSet

from .ast import TemplateAST, ASTNode, PresetExpr, TagLeaf, Text
from .context import ResolverContext
from .exceptions import PresetNotFoundError, RecursionLimitError

logger = logging.getLogger(__name__)

# PlaceholderとWildcardと同じ再帰深度制限
MAX_DEPTH = 20


class PresetEvaluator:
    """
    PresetExprをTagLeafに変換するエバリュエーター
    
    設計書4.2 ② PresetEval ステージの実装
    key_expr解析と左から右への演算処理を行う
    """
    
    def __init__(self, context: ResolverContext):
        self.context = context
        
    def evaluate_ast(self, ast: TemplateAST) -> TemplateAST:
        """
        ASTを走査してPresetExprをTagLeafに変換
        
        Args:
            ast: 入力AST
            
        Returns:
            PresetExpr → TagLeaf変換済みAST
        """
        result = []
        
        for node in ast:
            if isinstance(node, PresetExpr):
                try:
                    tags = self.parse_key_expr(node.key_expr)
                    result.append(TagLeaf(tags=tags))
                except PresetNotFoundError as e:
                    if self.context.strict_level == "error":
                        raise
                    elif self.context.strict_level == "warn":
                        logger.warning(f"PresetNotFound (fallback=empty): {e} | strict_level={self.context.strict_level}")
                        result.append(TagLeaf(tags=OrderedSet()))
                    else:  # soft
                        result.append(TagLeaf(tags=OrderedSet()))
                except ValueError as e:
                    # ValueErrorは常に再発生（クロスプリセット演算エラーなど）
                    logger.error(f"PresetEval error for key_expr='{node.key_expr}': {e}")
                    raise
                except Exception as e:
                    logger.error(f"PresetEval error for key_expr='{node.key_expr}': {e}")
                    if self.context.strict_level == "error":
                        raise
                    result.append(TagLeaf(tags=OrderedSet()))
            else:
                result.append(node)
                
        return result
    
    def parse_key_expr(self, key_expr: str) -> OrderedSet[str]:
        """
        key_expr文字列を解析してTagSetを生成
        
        Args:
            key_expr: "quality#base+hdr-unwanted" 形式の文字列
            
        Returns:
            計算結果のTagSet
            
        Raises:
            PresetNotFoundError: プリセットが見つからない場合（strict_level=errorのみ）
        """
        operations = self.tokenize_key_expr(key_expr)
        return self.evaluate_operations(operations)
    
    def tokenize_key_expr(self, key_expr: str) -> List[Tuple[str, Optional[str], str]]:
        """
        key_expr文字列をトークン化
        
        Args:
            key_expr: "quality#base+hdr-unwanted"
            
        Returns:
            [(preset_name, group_name, operator), ...] のリスト
            例: [("quality", "base", "+"), ("quality", "hdr", "+"), ("quality", "unwanted", "-")]
        
        Raises:
            ValueError: クロスプリセット演算が検出された場合
        """
        # 演算子で分割（+, -を保持）
        tokens = re.split(r'(\+|\-)', key_expr.strip())
        
        if not tokens:
            return []
        
        operations = []
        expected_preset = None  # 期待されるプリセット名（最初のトークンで確定）
        
        # 最初のトークンは演算子なし（デフォルトで+）
        first_token = tokens[0].strip()
        if first_token:
            preset_name, group_name = self._parse_group_token(first_token)
            expected_preset = preset_name  # 期待されるプリセット名を確定
            operations.append((preset_name, group_name, "+"))
        
        # 残りのトークンは演算子とペア
        i = 1
        while i < len(tokens) - 1:
            operator = tokens[i].strip()
            group_token = tokens[i + 1].strip()

            if operator in ["+", "-"] and group_token:
                # クロスプリセット演算の検出
                if '#' in group_token:
                    # 明示的にプリセット名が指定された場合
                    raise ValueError(f"Cross-preset operations are undefined: expected '{expected_preset}', got '{preset_name}' in '{key_expr}'")
                
                elif not group_name:
                    raise ValueError(f"Cross-preset operations are undefined: '{group_token}' appears to be a different preset in '{key_expr}'")
                
                elif  (group_token in ["+", "-"]):
                    # "+ -" のような連続演算子エラー
                    raise ValueError(f"Invalid key_expr: consecutive operators near '{operator}' in '{key_expr}'")
            elif not group_token:
                raise ValueError(f"Invalid key_expr: consecutive operators near '{operator}' in '{key_expr}'")

            operations.append((preset_name, group_token, operator))
            
            i += 2
        
        return operations
    
    def _parse_group_token(self, token: str) -> Tuple[str, Optional[str]]:
        """
        "preset#group" または "preset" を解析
        
        Args:
            token: "quality#base" または "quality"
            
        Returns:
            (preset_name, group_name_or_None)
        """
        if '#' in token:
            parts = token.split('#', 1)  # o3推奨: split('#', 1)で境界ケース対応
            preset_name = parts[0].strip()
            group_name = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
        else:
            preset_name = token.strip()
            group_name = None
            
        return preset_name, group_name
    
    def evaluate_operations(self, operations: List[Tuple[str, Optional[str], str]]) -> OrderedSet[str]:
        """
        左から右へ順次演算を実行
        
        Args:
            operations: [(preset_name, group_name, operator), ...]
            
        Returns:
            最終的なTagSet
        """
        result = OrderedSet()
        
        for preset_name, group_name, operator in operations:
            try:
                group_tags = self.resolve_group(preset_name, group_name)
                
                if operator == "+":
                    result |= group_tags  # union
                elif operator == "-":
                    result -= group_tags  # difference
                else:
                    logger.warning(f"Unknown operator '{operator}', treating as '+'")
                    result |= group_tags
                    
            except PresetNotFoundError as e:
                # エラー文言にstrict_levelとpreset#group情報を含める（o3推奨）
                group_ref = f"{preset_name}#{group_name}" if group_name else preset_name
                enhanced_msg = f"{e} | preset_ref={group_ref} | strict_level={self.context.strict_level}"
                
                if self.context.strict_level == "error":
                    raise PresetNotFoundError(enhanced_msg, preset_key=group_ref)
                elif self.context.strict_level == "warn":
                    logger.warning(f"PresetNotFound (fallback=empty): {enhanced_msg}")
                # soft の場合は何もしない（空集合として処理継続）
        
        return result
    
    def resolve_group(self, preset_name: str, group_name: Optional[str]) -> OrderedSet[str]:
        """
        プリセット名とグループ名からTagSetを解決
        ignore_groupsをここで適用（o3推奨）
        
        Args:
            preset_name: プリセット名
            group_name: グループ名（Noneの場合は全体）
            
        Returns:
            該当するTagSet
            
        Raises:
            PresetNotFoundError: プリセットまたはグループが見つからない場合
        """
        if preset_name not in self.context.presets:
            raise PresetNotFoundError(f"Preset '{preset_name}' not found")
        
        preset_file = self.context.presets[preset_name]
        
        if group_name is None:
            # グループ指定なしの場合は全グループのUnion
            all_tags = OrderedSet()
            for grp_name, grp_tags in preset_file.contents.items():
                # ignore_groups適用（o3推奨: Evaluator内で処理）
                if not self.context.should_ignore_group(grp_name):
                    all_tags.update(grp_tags)
            return all_tags
        else:
            # 特定グループ指定
            if group_name not in preset_file.contents:
                raise PresetNotFoundError(f"Group '{group_name}' not found in preset '{preset_name}'")
            
            # ignore_groups適用
            if self.context.should_ignore_group(group_name):
                return OrderedSet()  # 無視対象グループは空集合
            
            # 配列の各要素に対して再帰的にpreset展開を実行
            final_tags = OrderedSet()
            for tag in preset_file.contents[group_name]:
                if self._needs_reparse(tag):
                    try:
                        expanded_tags = self._parse_and_evaluate_recursive(tag)
                        final_tags.update(expanded_tags)
                    except RecursionLimitError:
                        # RecursionLimitErrorは常にre-raise
                        raise
                    except Exception as e:
                        logger.error(f"Failed to resolve nested preset '{tag}': {e}")
                        if self.context.strict_level == "error":
                            raise
                        # warn/softの場合は元タグを追加
                        final_tags.add(tag)
                else:
                    final_tags.add(tag)
            
            return final_tags
    
    def _needs_reparse(self, tag: str) -> bool:
        """
        preset構文が含まれているかチェック（PresetSubstitutorから移植）
        
        Args:
            tag: チェック対象の文字列
            
        Returns:
            <preset:xxx>構文が含まれている場合True
        """
        return '<preset:' in tag and '>' in tag
    
    def _parse_and_evaluate_recursive(self, tag: str) -> OrderedSet[str]:
        """
        タグ内のpreset構文を再帰的に展開（Parser使用版）
        
        Args:
            tag: 展開対象のタグ文字列
            
        Returns:
            展開済みTagSet
            
        Raises:
            RecursionLimitError: 再帰深度超過の場合
        """
        try:
            # 再帰深度管理
            self.context.reparse_depth += 1
            if self.context.reparse_depth > MAX_DEPTH:
                raise RecursionLimitError(
                    f"Preset reparse depth exceeded {MAX_DEPTH}",
                    depth=self.context.reparse_depth
                )
            
            # TemplateParserでAST化
            from .parser import TemplateParser
            parser = TemplateParser()
            current_ast = parser.parse(tag)
            
            # whileループで収束まで繰り返し処理（多段ネスト対応）
            max_iterations = MAX_DEPTH
            iteration = 0
            
            while self._ast_needs_reparse(current_ast) and iteration < max_iterations:
                iteration += 1
                
                # ASTを走査してPresetExprを展開
                new_ast = []
                for node in current_ast:
                    if isinstance(node, PresetExpr):
                        try:
                            # PresetExprを展開
                            expanded_tags = self.parse_key_expr(node.key_expr)
                            # 展開結果をTextノードとして追加
                            if expanded_tags:
                                expanded_text = ', '.join(expanded_tags)
                                from .ast import Text
                                new_ast.append(Text(value=expanded_text))
                        except Exception as e:
                            logger.warning(f"Failed to expand preset '{node.key_expr}': {e}")
                            if self.context.strict_level == "error":
                                raise
                            # エラー時は元のPresetExprを保持
                            new_ast.append(node)
                    else:
                        new_ast.append(node)
                
                current_ast = new_ast
                
                # 新しいASTから文字列を再構築してパース
                if self._ast_needs_reparse(current_ast):
                    reconstructed = self._reconstruct_from_ast(current_ast)
                    current_ast = parser.parse(reconstructed)
            
            # 反復制限に達した場合はRecursionLimitError
            if iteration >= max_iterations and self._ast_needs_reparse(current_ast):
                raise RecursionLimitError(
                    f"Preset expansion iteration limit exceeded {max_iterations}",
                    depth=iteration
                )
            
            # 最終ASTからTagSetを構築
            return self._collect_tags_from_ast(current_ast)
            
        finally:
            self.context.reparse_depth -= 1
    
    def _ast_needs_reparse(self, ast) -> bool:
        """ASTにPresetExprが含まれているかチェック"""
        from .ast import PresetExpr
        return any(isinstance(node, PresetExpr) for node in ast)
    
    def _reconstruct_from_ast(self, ast) -> str:
        """ASTから文字列を再構築"""
        parts = []
        for node in ast:
            if hasattr(node, 'value'):
                parts.append(node.value)
            elif hasattr(node, 'key_expr'):
                parts.append(f'<preset:{node.key_expr}>')
            else:
                parts.append(str(node))
        return ''.join(parts)
    
    def _collect_tags_from_ast(self, ast) -> OrderedSet[str]:
        """ASTからタグを収集"""
        final_tags = OrderedSet()
        for node in ast:
            if hasattr(node, 'value'):
                # Textノードの場合は分割して追加
                text = node.value.strip()
                if text:
                    tags = [t.strip() for t in text.split(',') if t.strip()]
                    final_tags.update(tags)
        return final_tags


