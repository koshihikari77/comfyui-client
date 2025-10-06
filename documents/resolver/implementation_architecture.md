# PromptResolver V2 実装アーキテクチャ

このドキュメントでは **PromptResolver V2** の内部実装とコード構成について説明します。6ステージパイプライン、AST処理、各クラスの技術詳細を記載しています。

---
## 1. アーキテクチャ概要

### 1.1 6ステージパイプライン
```
Template --(①Parse)--> AST --(②PresetEval)--> AST' --(③Placeholder)--> AST''
        --(④Wildcard)--> AST''' --(⑤Filter)--> TagSet --(⑥Format)--> Prompt
```

| ステージ | 入力 | 出力 | 担当クラス | 実装状況 |
|---------|------|------|-----------|----------|
| ① Parse | str | TemplateAST | `TemplateParser` | ✅ 完了 |
| ② PresetEval | AST | AST | `PresetEvaluator` | ✅ 完了 |
| ③ Placeholder | AST | AST | `PlaceholderSubstitutor` | ✅ 完了 |
| ④ Wildcard | AST | AST | `WildcardSubstitutor` | ✅ 完了 |
| ⑤ Filter | AST | TagSet | `TagFilter` | ✅ 完了 |
| ⑥ Format | TagSet | str | `PromptFormatter` | ✅ 完了 |

### 1.2 設計原則
- **純関数的設計**: 各ステージは副作用なし
- **ResolverContext**: 設定・状態を一元管理
- **AST変換**: 段階的なツリー変換処理
- **型安全性**: Pydantic BaseModelによる厳密な型定義

---
## 2. コード構成

### 2.1 モジュール構造
```
core/
├── prompt_resolver_v2.py      # メインファサード
├── resolver/
│   ├── __init__.py
│   ├── context.py             # ResolverContext
│   ├── ast.py                 # AST定義
│   ├── parser.py              # TemplateParser
│   ├── preset.py              # PresetEvaluator
│   ├── placeholder.py         # PlaceholderSubstitutor
│   ├── wildcard.py            # WildcardSubstitutor
│   ├── filter.py              # TagFilter
│   ├── formatter.py           # PromptFormatter
│   └── exceptions.py          # 例外階層
```

### 2.2 データモデル定義
```python
# core/resolver/context.py
class ResolverContext(BaseModel):
    presets: Dict[str, PresetFile]
    wildcards: Dict[str, List[str]]
    placeholders: Dict[str, List[str]] = {}
    rng: Random = Field(default_factory=Random)
    ignore_tags: Set[str] = set()
    ignore_groups: Set[str] = set()
    locale: Literal[",", "、", ";"] = ","
    strict_level: Literal["soft", "warn", "error"] = "warn"

# core/resolver/ast.py
class PresetFile(BaseModel):
    version: Literal[1, 2] = 2
    description: Optional[str] = None
    metadata: Dict[str, Any] = {}
    contents: Dict[str, List[str]]
```

---
## 3. 各ステージ実装詳細

### 3.1 ① Parse ステージ

#### 実装クラス: `TemplateParser`
```python
class TemplateParser:
    def parse(self, template: str) -> TemplateAST
    def validate_template(self, template: str) -> bool
```

#### 技術詳細
- **パーサー**: Lark LALR(1)パーサー
- **文法定義**: EBNF形式
- **AST生成**: TypedDict階層構造
- **エラー処理**: ParseError例外

#### EBNF文法
```ebnf
template : (text | preset | placeholder | wildcard)+
preset   : "<preset:" key_expr ">"
placeholder : "{" NAME "}"
wildcard : "__" NAME "__"
key_expr : GROUP ( ("+"|"-") GROUP )*
GROUP    : NAME ["#" NAME]
NAME     : /[A-Za-z0-9_\-\/]+/
```

#### 性能改善
- **validate_template高速化**: AST変換なしのLarkパーサー使用
- **キャッシュ機構**: LRUキャッシュ(50エントリ)

### 3.2 ② PresetEval ステージ

#### 実装クラス: `PresetEvaluator`
```python
class PresetEvaluator:
    def evaluate_ast(self, ast: TemplateAST) -> TemplateAST
    def tokenize_key_expr(self, key_expr: str) -> List[Tuple[str, Optional[str], str]]
    def _resolve_preset_groups(self, preset_key: str, group_expr: str) -> OrderedSet[str]
```

#### 技術詳細
- **グループ演算**: 左から右へ順次評価
- **集合演算**: OrderedSetによる効率的処理
- **ignore_groups統合**: フィルタリング機能

#### 実装修正記録
- **regex修正**: `r'(\+|\-)'` → `r'([+\-])'`パターン修正
- **トークン化問題解決**: 正確な演算子分割

### 3.3 ③ Placeholder ステージ

#### 実装クラス: `PlaceholderSubstitutor`
```python
class PlaceholderSubstitutor:
    def substitute_placeholders(self, ast: TemplateAST) -> Union[TemplateAST, List[TemplateAST]]
    def _parse_and_evaluate_recursive(self, choice: str) -> TemplateAST
    def _needs_reparse(self, text: str) -> bool
```

#### 技術詳細
- **sample/expandモード**: 設定による動作切替
- **多段ネスト対応**: while再帰による完全展開
- **メモリ制限**: isliceによる真の129件制限
- **深度制限**: MAX_DEPTH=20制限
- **LRUキャッシュ**: 50エントリによる性能向上

#### 再パース機能
- **Preset再パース**: `<preset:quality>`完全サポート
- **Placeholder再パース**: `{nested_placeholder}`サポート
- **Wildcard再パース**: `__nested_wildcard__`サポート

### 3.4 ④ Wildcard ステージ

#### 実装クラス: `WildcardSubstitutor`
```python
class WildcardSubstitutor:
    def substitute_wildcards(self, ast: TemplateAST) -> TemplateAST
    def _parse_and_evaluate_recursive(self, choice: str) -> TemplateAST
    def _needs_reparse(self, text: str) -> bool
```

#### 技術詳細
- **sampleモード**: ランダム選択
- **再パース機能**: Wildcard内でのPreset/Placeholder/Wildcard呼び出し
- **フォールバック保護**: `__undefined__`形式の無限再帰防止

### 3.5 ⑤ Filter ステージ

#### 実装クラス: `TagFilter`
```python
class TagFilter:
    def filter_ast(self, ast: TemplateAST) -> OrderedSet[str]
    def _collect_tagset_from_ast(self, ast: TemplateAST) -> OrderedSet[str]
    def _apply_ignore_tags(self, tagset: OrderedSet[str]) -> OrderedSet[str]
```

#### 技術詳細
- **AST→TagSet変換**: ツリー走査による統合
- **Text節点処理**: 分割せず単一要素として保持（仕様変更）
- **TagLeaf節点処理**: カンマ・読点分割
- **ignore_tags適用**: 高性能集合演算

#### 実装変更記録
- **Text節点仕様変更**: 当初分割処理想定→単一要素保持に変更
- **分割ロジック削除**: `_split_text_to_tags`メソッド削除

### 3.6 ⑥ Format ステージ

#### 実装クラス: `PromptFormatter`
```python
class PromptFormatter:
    def format_tagset(self, tagset: OrderedSet[str]) -> str
    def _join_with_locale(self, tags: List[str]) -> str
    def _validate_locale(self) -> str
    def _apply_formatting_options(self, tags: List[str]) -> List[str]
```

#### 技術詳細
- **TagSet→String変換**: 順序保持結合
- **locale対応**: 複数区切り文字サポート
- **重複除去**: OrderedSetによる効率的処理
- **将来拡張準備**: sort_alpha/shuffle枠組み

#### 実装仕様
- **単一要素時**: locale変換なし、元文字列保持
- **複数要素時**: 指定locale区切り文字で結合

---
## 4. エラーハンドリング

### 4.1 例外階層
```python
class ResolverError(BaseException):
    pass

class ParseError(ResolverError):
    pass

class PresetNotFoundError(ResolverError):
    pass

class PlaceholderError(ResolverError):
    pass

class WildcardError(ResolverError):
    pass

class RecursionLimitError(ResolverError):
    pass
```

### 4.2 strict_level処理
```python
def handle_error(self, error: ResolverError, context: ResolverContext):
    if context.strict_level == "error":
        raise error
    elif context.strict_level == "warn":
        logger.warning(f"Resolver warning: {error}")
        return ""  # 空文字返却
    elif context.strict_level == "soft":
        return ""  # サイレント処理
```

### 4.3 統合エラーハンドリング
- **空TagSet時**: 元テンプレート返却ロジック
- **各ステージ**: フォールバック処理統一
- **例外安全性**: 全ステージで保証

---
## 5. パフォーマンス対応

### 5.1 メモリ管理
- **islice制限**: 真の129件制限によるメモリ保護
- **LRUキャッシュ**: パーサー・置換結果の50エントリキャッシュ
- **OrderedSet**: 効率的集合演算・順序保持

### 5.2 処理性能
- **validate_template**: AST変換なしLarkパーサー使用
- **キャッシュ機構**: 再パース結果キャッシュ
- **効率的集合演算**: OrderedSetによる高速処理

### 5.3 深度制限
- **MAX_DEPTH=20**: 無限再帰防止
- **RecursionLimitError**: 深度超過時例外
- **while再帰**: 完全な多段展開

---
## 6. V1/V2互換性

### 6.1 ServiceContainer統合
```python
class ServiceContainer:
    def get_prompt_resolver(self) -> Union[PromptResolver, PromptResolverV2]:
        if self.config.use_v2:
            return PromptResolverV2(self.config)
        return PromptResolver(self.config)
```

### 6.2 V1形式自動変換
```python
def _load_presets(self) -> Dict[str, PresetFile]:
    # V1形式: list → V2形式変換
    if isinstance(data, list):
        preset_file = PresetFile(
            version=1,
            contents={"__all__": data}
        )
```

### 6.3 ファイルパス階層
```python
key = str(file_path.relative_to(presets_dir)).replace('.yaml', '').replace('\\', '/')
# character/akira/school_uniform.yaml → character/akira/school_uniform
```

---
## 7. テスト戦略

### 7.1 テスト構成
```
tests/
├── test_prompt_resolver_v2_integration.py  # V2統合テスト(9件)
└── resolver/                               # 個別ステージテスト(236件)
    ├── test_parser.py                      # Parse(75件)
    ├── test_preset_evaluator.py            # PresetEval(21件)
    ├── test_placeholder.py                 # Placeholder(37件)
    ├── test_wildcard.py                    # Wildcard(21件)
    ├── test_filter.py                      # Filter(21件)
    └── test_formatter*.py                  # Format(61件)
```

### 7.2 テストカテゴリ
- **基本機能**: 各ステージの核心機能
- **エラーハンドリング**: strict_level別処理・例外安全性
- **境界値**: 空入力・大規模データ・Unicode
- **統合**: ステージ間連携・パイプライン動作
- **再現性**: シード値による一貫性確認

### 7.3 V2統合テスト詳細
- **V2パイプライン統合**: 6ステージ完全動作確認
- **V1/V2切替**: ServiceContainer経由の互換性テスト
- **プリセットV2形式**: フラット構造仕様準拠テスト
- **locale対応**: 複数区切り文字サポート確認
- **strict_level**: 3段階エラーハンドリング検証

---
## 8. 実装時判明の技術課題と解決

### 8.1 PresetEvaluator regex問題
**問題**: `r'(\+|\-)'`パターンで`base+hdr`が正しく分割されない
**原因**: `+`が量詞として解釈される
**解決**: `r'([+\-])'`文字クラス使用に修正

### 8.2 Filter Text節点処理
**問題**: 当初想定していた自動分割が意図しない結果を生成
**解決**: Text節点は分割せず単一要素として保持に仕様変更

### 8.3 validate_template性能問題
**問題**: `validate_template`が`parse`より遅い
**原因**: 内部でフルAST変換を実行
**解決**: Larkパーサーのみ使用、AST変換スキップ

### 8.4 locale処理精度向上
**問題**: 単一要素でも区切り文字変換が実行される
**解決**: 単一要素時は元文字列保持、複数要素時のみlocale変換

### 8.5 strict_level動作拡張
**問題**: 空TagSet時の処理が未定義
**解決**: 空TagSet検出時に元テンプレート返却ロジック追加

---
## 9. Constant機能 実装詳細（v2.8新機能）

### 9.1 アーキテクチャ概要
Constant機能は`SequenceJobExecutor`専用の最初のプリプロセッサとして実装されています。

**処理フロー:**
```
JobConfig --読込--> Constants --実行時--> ConstantSubstitution --置換--> Template'
                                                                      ↓
                                                             IteratorSubstitution --置換--> Template'' --V2Pipeline--> Result
```

### 10.2 実装箇所

#### 10.2.1 設定モデル拡張
- **ファイル**: `core/schemas/config_models.py`
- **追加フィールド**: `JobConfigModel.constants: Optional[Dict[str, str]]`
- **バリデーション**: constant名の文字列検証、値の文字列検証

#### 9.2.2 Config拡張
- **ファイル**: `core/config.py` 
- **追加プロパティ**: `constants: dict`
- **戻り値**: `self.job_config_model.constants`

#### 9.2.3 SequenceJobExecutor拡張
- **ファイル**: `core/executors/sequence_executor.py`
- **新メソッド**: `_substitute_constant_syntax(template: str) -> str`
- **処理順序**: Constant → Iterator → V2Pipeline

### 9.3 置換アルゴリム

#### 9.3.1 記法検出
```python
pattern = r'%([a-zA-Z_][a-zA-Z0-9_]*)%'
```

**マッチング例:**
- `%base_quality%` → グループ1: `base_quality`
- `%base_character%` → グループ1: `base_character`
- `%invalid-name%` → マッチしない（ハイフン不可）

#### 9.3.2 置換処理
```python
def replace_constant(match):
    constant_name = match.group(1)
    if constant_name in constants:
        return constants[constant_name]
    else:
        # 警告ログ出力
        logger.warning(f"Constant '{constant_name}' が見つかりません")
        return match.group(0)  # 元の文字列を返す
```

**特徴:**
- 未定義constant警告（エラーではない）
- 部分置換対応
- エスケープ不要

### 9.4 設定例とユースケース

#### 9.4.1 基本使用例
```yaml
constants:
  base_quality: "masterpiece, best quality, amazing quality"
  base_character: "1girl, shiina yuika"

prompts:
  - template: "%base_character%, %base_quality%, happy"
    runs: 3
```

#### 9.4.2 組み合わせ例
```yaml
constants:
  base_setup: "1girl, <preset:quality>"

iterators:
  emotion: ["happy", "sad"]

prompts:
  - template: "%base_setup%, $[emotion], sitting"
    runs: 4
```

**処理順序:**
1. `%base_setup%` → `"1girl, <preset:quality>"`
2. `$[emotion]` → `"happy"` (1回目)
3. `<preset:quality>` → V2Pipeline処理

---
## 10. Iterator機能 実装詳細（v2.7新機能）

### 10.1 アーキテクチャ概要
Iterator機能は`SequenceJobExecutor`専用のプリプロセッサとして実装されています。

**処理フロー:**
```
JobConfig --読込--> IteratorResolver --事前処理--> 解決済Iterator
                                                        ↓
Template --実行時--> IteratorSubstitution --置換--> Template' --V2Pipeline--> Result
```

### 9.2 実装クラス

#### 9.2.1 SequenceJobExecutor拡張
- **新フィールド**: `_resolved_iterators: Dict[str, List[str]]`
- **新メソッド**: `_preprocess_iterators()`, `_substitute_iterator_syntax()`
- **統合ポイント**: 既存の`_build_params()`前に処理実行

#### 9.2.2 PromptResolverV2拡張
- **新メソッド**: `get_preset_groups(preset_key: str) -> List[str]`
- **役割**: expand_preset機能のサポート
- **動作**: PresetFileのcontentsキーを定義順で取得

### 9.3 データモデル

#### 9.3.1 JobConfigModel
```python
iterators: Optional[Dict[str, Union[List[str], IteratorItemModel]]] = Field(
    default={}, 
    description="Iterator定義"
)
```

#### 9.3.2 IteratorItemModel
```python
class IteratorItemModel(BaseModel):
    expand_preset: str = Field(..., min_length=1, description="展開するプリセット名")
```

### 9.4 処理アルゴリズム

#### 9.4.1 事前処理（_preprocess_iterators）
```python
def _preprocess_iterators(self) -> Dict[str, List[str]]:
    """
    1. 手動リスト → そのまま使用
    2. expand_preset → get_preset_groups() → preset参照形式に変換
    """
```

#### 9.4.2 置換処理（_substitute_iterator_syntax）
```python
def _substitute_iterator_syntax(self, template: str, iteration_index: int) -> str:
    """
    正規表現: r'\$\[([a-zA-Z_][a-zA-Z0-9_]*)\]'
    巡回ロジック: iteration_index % len(iterator_list)
    """
```

### 9.5 パフォーマンス最適化

- **事前処理**: ジョブ開始時に1回のみIterator解決
- **実行時処理**: 単純な文字列置換（regex）のみ
- **メモリ効率**: 解決済みリストをインスタンス変数で保持

### 9.6 エラーハンドリング

- **未定義Iterator**: 警告ログ出力、元文字列保持
- **空Iterator**: 警告ログ出力、元文字列保持
- **expand_preset失敗**: エラーログ出力、空リストで継続

### 9.7 V2パイプラインとの連携

Iterator置換は**V2パイプライン前**に実行されるため：
```
$[location] → "in library" → <preset:quality>, 1girl, in library → (V2処理)
```

expand_presetで生成されたpreset参照も通常のV2処理で解決されます。

---
## 10. 依存ライブラリ

### 10.1 コアライブラリ
```python
lark==1.1.7                    # パーサー
pydantic==1.10.13              # データ検証
python-ordered-set==4.1.0      # 順序付き集合
```

### 10.2 テストライブラリ
```python
pytest==7.4.3                 # テストフレームワーク
hypothesis==6.99.2             # プロパティベーステスト
```

---
## 10. V2完成記録（2025-07-19）

### 10.1 実装完了状況
- ✅ **Parse**: Lark LALR(1)パーサー・AST生成・パフォーマンス向上
- ✅ **PresetEval**: グループ演算・ignore_groups統合・regex修正
- ✅ **Placeholder**: sample/expandモード・多段ネスト・メモリ制限
- ✅ **Wildcard**: sampleモード・再パース機能・フォールバック保護
- ✅ **Filter**: AST→TagSet変換・ignore_tags適用・Text節点対応
- ✅ **Format**: TagSet→String変換・locale対応・将来拡張準備
- ✅ **統合**: 6ステージパイプライン統合・V2問題修正完了

### 10.2 テスト完了状況
- **総テスト数**: 245テスト
- **成功率**: 100%
- **網羅範囲**: 全ステージ個別テスト + V2統合テスト

### 10.3 性能・安全性
- **メモリ安全**: islice制限・LRUキャッシュ・深度制限
- **例外安全**: 全ステージでエラーハンドリング
- **型安全**: Pydantic BaseModelによる厳密な型定義
- **再現性**: RNGシード値による一貫した結果

---
## 11. 将来拡張準備

### 11.1 Formatter拡張枠組み
```python
def _apply_formatting_options(self, tags: List[str]) -> List[str]:
    # sort_alpha: アルファベット順ソート機能
    # shuffle: シャッフル機能（RNG使用）
    # 実装準備済み
```

### 11.2 グループ内ドット記法サポート準備
- tokenize_key_exprメソッドでの階層構造解析準備
- `#style.anime`形式の将来実装枠組み

### 11.3 性能監視準備
- 大規模データでの性能回帰テスト枠組み
- メモリ使用量監視機構

---
(End of Document)