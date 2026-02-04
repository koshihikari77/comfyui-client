---
name: sequence-placeholder-mixed
overview: Sequenceでもplaceholderを直積展開できるようにし、同一プロンプト内で直積（デフォルト）とランダム（`{name:r}`）を混在できるようにします。wildcard/iteratorは現状どおりランダム/巡回のまま。
todos:
  - id: grammar-placeholder-mode
    content: template.lark / ast.py / parser.py を更新し `{name:r}` をパースできるようにする
    status: pending
  - id: placeholder-mixed-expand
    content: placeholder.py に mixed（expandデフォルト + :rはsample）を実装し、上限をデフォルト値として整理
    status: pending
  - id: resolver-resolve-many
    content: prompt_resolver_v2.py に resolve_many を追加し、expand_placeholders も正しいモードで動くよう整理
    status: pending
  - id: sequence-use-resolve-many
    content: sequence_executor.py と main.py(--dump-prompts) を resolve_many 対応にする
    status: pending
  - id: tests-placeholder-mixed
    content: mixed placeholder の単体テスト/回帰テストを追加
    status: pending
  - id: docs-placeholder-mixed
    content: config_and_prompt_guide.md に `{name}`/`{name:r}` と runs/上限の注意を追記
    status: pending
isProject: false
---

## ゴール

- `job_type: sequence` で `{placeholder}` を **直積（expand）がデフォルト**として扱い、同一プロンプト内で混在できるようにする。
- **ランダムにしたいplaceholderだけ** `{name:r}` で指定する（A1: 直積の各組み合わせごとにランダム選択してよい）。
- wildcard / iterator の挙動は **変更しない**。
- `default_runs` と `_runs` の優先度は現状どおり（個別が優先）。
- 直積の上限（展開数）は **デフォルト値**を持ち、必要なら設定で上書きできる形にする。

## 方針（重要）

- `IPromptResolver.resolve()` は `str` 返却のため、**複数展開を返すAPIを追加**して Sequence 側がそれを使う。
  - `PromptResolverV2.resolve_many()`（新規）: `List[str]` を返す
  - Sequence/--dump-prompts は `resolve_many()` があればそれを使い、無ければ従来どおり `resolve()`

## 仕様

- Placeholder構文:
  - `{name}`: **expand（直積）**
  - `{name:r}`: **sample（ランダム1つ）**
- 直積対象は `{name}` のみ。
- `{name:r}` は **各直積組み合わせごとに**ランダム選択（A1）。
- 展開総数には上限（例: 128）を適用し、超えたらエラー（既存の `MAX_EXPANSION` をベースに整理）。

## 実装タスク

- 文法/AST/パーサ拡張
  - `[/home/inada/win_obs/03_projects/comfyui/core/resolver/template.lark](/home/inada/win_obs/03_projects/comfyui/core/resolver/template.lark)`
    - `placeholder: "{" NAME (":" PLACEHOLDER_MODE)? "}"`
    - `PLACEHOLDER_MODE: "r"`
  - `[/home/inada/win_obs/03_projects/comfyui/core/resolver/ast.py](/home/inada/win_obs/03_projects/comfyui/core/resolver/ast.py)`
    - `Placeholder` に `mode`（`"expand"|"sample"`）を追加（`:r` → sample、未指定 → expand）
  - `[/home/inada/win_obs/03_projects/comfyui/core/resolver/parser.py](/home/inada/win_obs/03_projects/comfyui/core/resolver/parser.py)`
    - `TemplateTransformer.placeholder()` で children 長さに応じて `Placeholder(mode=...)` を生成
- PlaceholderSubstitutor の mixed 展開
  - `[/home/inada/win_obs/03_projects/comfyui/core/resolver/placeholder.py](/home/inada/win_obs/03_projects/comfyui/core/resolver/placeholder.py)`
    - expand group（mode=expand）だけ直積し、sample group（mode=sample）を各組み合わせに対してランダム適用
    - `MAX_EXPANSION`（上限）を **デフォルト値**として維持し、`ResolverContext` などから上書きできる形に整理
- PromptResolverV2 に複数解決APIを追加
  - `[/home/inada/win_obs/03_projects/comfyui/core/prompt_resolver_v2.py](/home/inada/win_obs/03_projects/comfyui/core/prompt_resolver_v2.py)`
    - `resolve_many(template_string) -> List[str]` を追加（Parse→PresetEval→Placeholder(mixed)→Wildcard→Filter→Format をASTごとに回す）
    - `expand_placeholders()` が sample になっている現状の不整合も合わせて整理（expand/mixed を正しく使う）
- Sequence / dump-prompts 側で `resolve_many()` を利用
  - `[/home/inada/win_obs/03_projects/comfyui/core/executors/sequence_executor.py](/home/inada/win_obs/03_projects/comfyui/core/executors/sequence_executor.py)`
    - 1回の run で `resolve_many()` が複数返す場合は、返ってきた各 prompt を順に実行
    - runs との関係は「展開後の各 prompt に対して runs を適用」（= 直積×runs）
  - `[/home/inada/win_obs/03_projects/comfyui/main.py](/home/inada/win_obs/03_projects/comfyui/main.py)`
    - `--dump-prompts` の生成ロジックでも `resolve_many()` があれば使う
- テスト
  - `core/resolver/placeholder.py` の mixed 展開（expandと:r混在）が期待どおりの個数/内容になる
  - Sequence で expand が複数返った場合の実行順（ダンプで検証）
- ドキュメント
  - `[/home/inada/win_obs/03_projects/comfyui/documents/config_and_prompt_guide.md](/home/inada/win_obs/03_projects/comfyui/documents/config_and_prompt_guide.md)`
    - `{name}` が直積、`{name:r}` がランダムの説明と注意（上限・直積×runs）

---

## 実装結果（完了）

方針は「resolve_many で複数返す」ではなく **resolve_nth(template, n, cycle)** で n 番目の直積を1本返す形で実装した（1 run = 1 枚の現行モデルを維持）。

### 変更ファイル

| 対象 | 内容 |
|------|------|
| **template.lark** | `placeholder: "{" NAME (":" PLACEHOLDER_MODE)? "}"`、`PLACEHOLDER_MODE: "r"` を追加 |
| **ast.py** | `Placeholder` に `mode: str = "expand"` を追加（`:r` 時は `"sample"`） |
| **parser.py** | `placeholder()` で children 長に応じて `Placeholder(name=..., mode=...)` を生成 |
| **placeholder.py** | `count_expand_combinations(ast)`、`substitute_mixed_nth(ast, n, cycle, max_expansion)` を追加。`_substitute_expand` を node.mode 対応に変更。`DEFAULT_MAX_EXPANSION = 128`。 |
| **context.py** | `ResolverContext` に `placeholder_max_expansion: int = 128` を追加 |
| **prompt_resolver_v2.py** | `resolve()` は `substitute_mixed_nth(ast, 0, cycle=True)` で単一文字列を返す。`resolve_nth(template_string, n, cycle=True, placeholders=None)` を新規追加。`expand_placeholders()` は `count_expand_combinations` + `substitute_mixed_nth(n)` の列挙で全組み合わせを返す。config に `placeholder_max_expansion` を追加。 |
| **sequence_executor.py** | `_build_params(template, iteration_index, local_run_index, prompt_def)` に変更。`resolve_nth(template, local_run_index, cycle=True)` を使用。 |
| **main.py** | `generate_resolved_prompts` で `resolve_nth(processed, i, cycle=True)` を使用。 |
| **interfaces.py** | `IPromptResolver` に `resolve_nth(...)` のデフォルト実装（`resolve_full` に委譲）を追加。 |
| **config_and_prompt_guide.md** | 6.2 Placeholder を `{name}`（直積）/ `{name:r}`（ランダム）に更新。runs は上限・cycle の説明、`placeholder_max_expansion` の説明を追記。4.2 に runs の意味を追記。 |

### テスト

- **test_parser_basic.py** / **resolver/test_parser.py**: `{name}` の `mode=="expand"`、`{name:r}` の `mode=="sample"` を検証。
- **resolver/test_placeholder.py**: `TestCountExpandCombinationsAndSubstituteMixedNth` を追加（count、substitute_mixed_nth、cycle、order、expand+sample 混在、max_expansion 超過）。
- **test_executors.py**: `_build_params` 呼び出しを 4 引数（template, iteration_index, local_run_index, prompt_def）に統一。

### 破壊的変更

- **`{name}`** のデフォルトが「ランダム1つ」から **「直積の n 番目を順に使用」** に変更。従来どおりランダムにしたい場合は **`{name:r}`** に移行すること。

