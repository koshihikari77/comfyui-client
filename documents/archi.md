

はい、承知いたしました。
シニアソフトウェアエンジニアとして、現在のプロジェクト**「ComfyV」**の仕様、アーキテクチャ、および機能を最新の状態に更新して要約します。

---

### プロジェクト概要：ComfyV (Comfy Verifier) - v2.1

**ComfyV**は、ComfyUI APIを利用した、**拡張性の高い自動画像生成・検証フレームワーク**です。v2.0から更に進化し、責務分離の徹底、型安全性の向上、レポート生成機能の独立化により、より保守性が高く拡張可能なアーキテクチャを実現しています。

**目的:**
*   **体系的な検証の自動化**: LoRA、プロンプト、サンプラー設定など、複数のパラメータが画像生成に与える影響を、全組み合わせ（グリッドサーチ）またはシーケンシャルに自動で検証します。
*   **プロンプト生成の効率化**: プリセットやワイルドカード、プレースホルダーといった機能を駆使し、少ない記述量で多様なプロンプトを体系的に生成します。
*   **再現性とデータ管理**: 全ての生成結果（画像、使用したワークフロー、パラメータ）をデータベースに記録し、完全な再現性を確保します。

---

### アーキテクチャと設計思想

v2.1では、**ストラテジーパターン**と**コンポーネントベースアーキテクチャ**をさらに発展させ、責務分離の徹底と型安全性の向上を実現しています。

1.  **Executorの分離（ストラテジーパターン）**:
    *   ジョブの実行ロジックを`BaseExecutor`という抽象基底クラスに定義。
    *   具体的な実行戦略として`GridSearchJobExecutor`（全組み合わせ検証）と`SequenceJobExecutor`（逐次実行）を実装。
    *   `config.yaml`の`job_type`キーによって実行時にどの戦略（Executor）を使用するかを切り替えることができ、将来的に新しい実行戦略を簡単に追加可能。

2.  **プロンプト解決の統一API（v2.1新機能）**:
    *   プロンプトのテンプレート解決（プリセット、ワイルドカード）ロジックを`PromptResolver`クラスに完全に分離。
    *   v2.1では`resolve_full()`と`expand_placeholders()`の統一APIを追加し、Executorからの呼び出しを一本化。
    *   Executorはプロンプトの複雑な生成ロジックを意識する必要がなく、単純にResolverを呼び出すだけでよくなりました。
    *   **v2.2アップデート**: 6ステージパイプライン（Parse → PresetEval → Placeholder → Wildcard → Filter → Format）による高度な処理を実装。
    *   **v2.3アップデート**: PlaceholderSubstitutor完全実装（再パース機能・多段ネスト・メモリ最適化）、WildcardSubstitutor完全実装（sampleモード・再パース機能）により、高度なテンプレート処理を実現。
    *   **v2.4アップデート**: TagFilter完全実装（ignore_tags機能・再パース統合・高性能化）、PromptFormatter完全実装（locale対応・将来拡張準備・包括的テスト）により、**6ステージパイプライン完全完成**。

3.  **設定駆動の強化とPydantic型安全性（v2.1新機能）**:
    *   `config.yaml`がフレームワークの動作を完全に制御します。`job_type`の指定から、`placeholders`による動的なプロンプト生成、`fixed_parameters`による共通設定まで、YAMLファイルの記述のみで多様なユースケースに対応します。
    *   v2.1では**Pydantic**による設定値の型安全性とバリデーションを導入し、設定ミスの早期発見と開発効率向上を実現。
    *   **v2.5完了**: PromptResolver V2完全実装（6ステージパイプライン統合、245テスト100%PASS、V1/V2完全互換性確保）。

4.  **モジュール化されたレポート生成（v2.1新機能）**:
    *   レポート生成機能を`core/reporting/`モジュールに分離し、`BaseReportGenerator`抽象クラスと`HTMLReportGenerator`実装を提供。
    *   `Reporter`ファサードクラスにより、Executorからのレポート生成呼び出しを統一化。

5.  **堅牢なデータ永続化**:
    *   各画像生成時に使用された**最終的なパラメータ**（プロンプト解決後）もデータベースの`images`テーブルに記録するよう拡張。これにより、画像からパラメータへの追跡がより容易になりました。

---

### プロジェクトの構成要素（v2.1）

```
comfyv/
├── main.py                 # エントリーポイント。job_typeに応じて適切なExecutorを起動する。
│
├── core/
│   ├── config.py             # Configクラス: Pydantic統合による型安全な設定管理。
│   ├── database.py           # DatabaseManagerクラス: パラメータ保存カラムを追加したDBを操作。
│   ├── api_client.py         # ComfyUI_APIClientクラス: ComfyUIとの通信。
│   ├── prompt_resolver.py    # PromptResolverクラス: V1実装（統一API）。
│   ├── prompt_resolver_v2.py # PromptResolverV2クラス: 6ステージパイプライン統合。
│   ├── service_container.py  # ServiceContainer: V1/V2切替機能。
│   ├── interfaces.py         # インターフェース定義。
│   ├── mock_services.py      # モックサービス（テスト用）。
│   │
│   ├── resolver/             # [v2.2新設] 6ステージパイプライン実装
│   │   ├── __init__.py           # モジュール初期化
│   │   ├── ast.py                # AST定義（Text, PresetExpr, Placeholder, Wildcard, TagLeaf）
│   │   ├── context.py            # ResolverContext, PresetFile
│   │   ├── exceptions.py         # 例外階層（ParseError, PresetNotFoundError等）
│   │   ├── parser.py             # ① Parse: TemplateParser実装
│   │   ├── preset.py             # ② PresetEval: PresetEvaluator実装
│   │   ├── placeholder.py        # ③ Placeholder: PlaceholderSubstitutor実装
│   │   ├── wildcard.py          # ④ Wildcard: WildcardSubstitutor実装
│   │   ├── filter.py            # ⑤ Filter: TagFilter実装
│   │   ├── formatter.py         # ⑥ Format: PromptFormatter実装
│   │   └── template.lark         # Lark文法定義
│   │
│   ├── schemas/              # [v2.1新設] Pydantic型定義
│   │   └── config_models.py      # 設定値のバリデーションモデル
│   │
│   ├── reporting/            # [v2.1新設] レポート生成モジュール
│   │   ├── __init__.py           # モジュール初期化
│   │   ├── base.py               # BaseReportGenerator抽象クラス
│   │   ├── html.py               # HTMLReportGenerator実装
│   │   └── reporter.py           # Reporterファサードクラス
│   │
│   └── executors/            # Executorを格納するパッケージ
│       ├── __init__.py           # モジュール初期化
│       ├── base_executor.py      # BaseExecutor(ABC): Reporter統合済み共通基盤。
│       ├── grid_search_executor.py # GridSearchJobExecutor: 統一API使用。
│       └── sequence_executor.py  # SequenceJobExecutor: 設定リストを順に実行。
│
├── prompts/                  # [新設] PromptResolverが参照するファイル群
│   ├── presets/              # プリセット定義用のYAMLファイル。
│   └── wildcards/            # ワイルドカード用のTXTファイル。
│
├── results/                  # 出力結果
│   ├── images/
│   └── index.sqlite
│
├── templates/
│   └── report.html.j2        # レポートテンプレート。
│
├── tests/                    # テストスイート（245テスト、成功率100%）
│   ├── __init__.py
│   ├── conftest.py               # pytest設定
│   ├── test_config.py            # Config関連テスト
│   ├── test_executors.py         # Executor関連テスト
│   ├── test_mock_services.py     # MockServices関連テスト
│   ├── test_prompt_resolver.py   # PromptResolver V1テスト
│   ├── test_prompt_resolver_v2_integration.py # PromptResolver V2統合テスト（9テスト）
│   ├── test_reporting.py         # レポート生成テスト
│   │
│   ├── integration/              # 統合テスト
│   │   └── test_main_integration.py # メイン統合テスト
│   │
│   └── resolver/                 # PromptResolver V2個別テスト（236テスト）
│       ├── __init__.py
│       ├── test_error_handling.py    # エラーハンドリングテスト
│       ├── test_filter.py            # TagFilterテスト（21テスト）
│       ├── test_filter_basic.py      # TagFilter基本テスト
│       ├── test_filter_errors.py     # TagFilterエラーテスト
│       ├── test_filter_ignore.py     # TagFilter ignore機能テスト
│       ├── test_formatter.py         # PromptFormatterテスト（24テスト）
│       ├── test_formatter_basic.py   # PromptFormatter基本テスト（13テスト）
│       ├── test_formatter_errors.py  # PromptFormatterエラーテスト（13テスト）
│       ├── test_formatter_future.py  # PromptFormatter将来拡張テスト（11テスト）
│       ├── test_parser.py            # TemplateParserテスト（75テスト）
│       ├── test_performance.py       # パフォーマンステスト
│       ├── test_placeholder.py       # PlaceholderSubstitutorテスト（37テスト）
│       ├── test_preset_evaluator.py  # PresetEvaluatorテスト（21テスト）
│       └── test_wildcard.py          # WildcardSubstitutorテスト（21テスト）
│
├── documents/                # プロジェクト仕様書
│   ├── archi.md                  # アーキテクチャ仕様（本ドキュメント）
│   ├── debug.md                  # デバッグガイド
│   ├── implementation_work_log.md # V2実装作業ログ
│   └── resolver/                 # Resolver仕様書
│       └── prompt_format.md      # プロンプト形式仕様（作成予定）
│
└── ... (configs/, workflows/)
```

### 機能仕様とユースケース

#### 1. グリッドサーチ (`job_type: grid_search`)
複数のパラメータ軸の全組み合わせを網羅的にテストします。LoRAの比較や、特定のパラメータ間の相互作用を調べるのに最適です。

*   **`variables`**: 複数の変動軸をリストで定義。
*   **`placeholders`**: プロンプトテンプレート内の`{placeholder}`を、定義された値のリストに展開し、組み合わせの次元をさらに増やすことが可能。
*   **`fixed_parameters`**: グリッド全体で共通の設定（Negative PromptやSeedなど）を適用。
*   **プロンプト解決**: ワイルドカード (`__wildcard__`) を使って、各生成でプロンプトにランダムな要素を加えることが可能。

#### 2. シーケンス実行 (`job_type: sequence`)
定義されたプロンプトや設定のリストを上から順に1回ずつ実行します。アイデア出しや、特定のテーマに沿った画像を複数枚生成するのに適しています。

*   **`prompts`**: `template`と`runs`（実行回数）を含むリストを定義。
*   **`random_parameters`**: 実行ごとに特定のパラメータ（Seed値など）をランダムに変化させ、多様な結果を得ることが可能。
*   **プロンプト解決**: グリッドサーチと同様に、プリセットやワイルドカードを利用可能。

このv2.1のアーキテクチャにより、ComfyVは単なる「検証ツール」から、**型安全性とモジュール性を備えた高度な設定駆動型自動画像生成エンジン**へと進化しました。

はい、承知いたしました。
データベーススキーマはプロジェクトのデータ構造の根幹をなすため、仕様書に含めることは非常に重要です。

現在のComfyV v2.0の仕様に基づき、`results/index.sqlite`内に定義されているデータベースのスキーマ情報を詳細に記述します。

---

### データベース仕様 (SQLite)

ComfyVの全てのメタデータは、単一のSQLiteデータベースファイル (`results/index.sqlite`) に集約されます。このデータベースは、**ジョブ (Jobs)** と **画像 (Images)** という2つの主要なエンティティ（実体）を管理するためのテーブルで構成されています。

**v2.5アップデート（2025-07-19）**: PromptResolver V2完全実装により、より高度なプロンプト生成とテンプレート処理が可能になりました。

#### テーブル1: `jobs`

このテーブルは、実行された各「検証ジョブ」のマスター情報を記録します。`main.py`が実行されるたびに、ここに1行のレコードが作成されます。

| カラム名 | データ型 | 説明 | 主キー |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | **ジョブID**。自動でインクリメントされるユニークな通し番号。 | ✔️ PK |
| `name` | TEXT | **ジョブ名**。`config.yaml`の`job_name`から取得される、人間が識別しやすい名前。 | |
| `config` | TEXT | **ジョブ設定**。このジョブを実行するために使用された`config.yaml`の内容全体がJSON形式の文字列で保存される。これにより、ジョブの完全な再現性が保証される。 | |
| `status` | TEXT | **ジョブのステータス**。`running`, `completed`, `failed` のいずれかの値を取る。 | |
| `created_at` | TIMESTAMP| **ジョブ開始日時**。このレコードが作成された日時。 | |

**インデックス:**
*   `id` (主キーインデックス)

**役割:**
*   過去に実行したジョブを一覧し、管理するための台帳。
*   各画像がどのジョブに属しているかを紐付けるための親テーブル。
*   `config`カラムを参照することで、全く同じジョブを再実行することが可能。

---

#### テーブル2: `images`

このテーブルは、生成された**個々の画像一枚一枚**に関する全ての詳細情報を記録します。このテーブルがComfyVのデータ資産の核となります。

| カラム名 | データ型 | 説明 | 主キー |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | **画像ID**。自動でインクリメントされるユニークな通し番号。画像ファイル名 (`00000001.png`など) と対応する。 | ✔️ PK |
| `job_id` | INTEGER | **外部キー**。この画像が属する`jobs`テーブルの`id`。 | |
| `filepath` | TEXT | **ファイルパス**。プロジェクトルートからの相対パス (例: `results/images/00000001.png`)。 | |
| `workflow` | TEXT | **実行ワークフロー**。この画像を生成するために、実際にComfyUI APIに送信された、パラメータ適用後の**完全なワークフロー**がJSON形式の文字列で保存される。究極の再現性を提供。 | |
| `parameters`| TEXT | **適用パラメータ**。この画像を生成するために`Executor`が解決した、キーと値のペアがJSON形式の文字列で保存される (例: `{"116.lora_name_1": "lora.safetensors", "171.seed": 12345}` )。検索や分析に利用。 | |
| `status` | TEXT | **画像の生成ステータス**。`pending`, `success`, `failed` のいずれかの値を取る。 | |
| `created_at`| TIMESTAMP| **画像生成日時**。このレコードが作成された日時。 | |

**インデックス:**
*   `id` (主キーインデックス)
*   `job_id` (外部キーインデックス。特定のジョブに属する画像を高速に検索するために推奨)

**役割:**
*   全ての生成画像を管理するためのマスターテーブル。
*   `workflow`カラムにより、**いつでも全く同じ画像を再生成**することが可能。
*   `parameters`カラムにより、「特定のLoRAを使った画像」や「特定のシード値の画像」などを**高速に検索・フィルタリング**することが可能。
*   レポート生成や、将来的なデータ分析機能のデータソースとなる。

---

### データ間の関係性 (リレーション)

```
+-----------+       +----------------+
|   jobs    |       |     images     |
+-----------+       +----------------+
| id (PK)   |-------<| job_id (FK)    |
| name      |       | id (PK)        |
| config    |       | filepath       |
| status    |       | workflow       |
| created_at|       | parameters     |
+-----------+       | status         |
                    | created_at     |
                    +----------------+
```
*   1つの`jobs`レコードに対して、複数の`images`レコードが関連付けられます (一対多の関係)。

このスキーマ設計により、ComfyVは単純な画像生成ツールではなく、生成プロセス全体を記録・管理・再利用できる、体系的なデータ管理プラットフォームとしての基盤を確立しています。


### ComfyV ジョブ設定 (`config.yaml`) ガイド

ComfyVの動作は、単一のYAMLファイルによって完全に制御されます。以下は、設定可能な全キーとその役割についての詳細なリファレンスです。

#### 1. 全ジョブ共通のトップレベルキー

これらのキーは、どの`job_type`でも必須または共通して使用します。

| キー | 型 | 必須 | 説明 |
| :--- | :--- | :--- | :--- |
| `job_type` | string | No | ジョブの実行戦略を決定します。`"grid_search"`または`"sequence"`を指定。省略した場合は`"grid_search"`として扱われます。 |
| `job_name` | string | Yes | このジョブを識別するための人間が読みやすい名前。DBやレポートファイル名に使用されます。 |
| `base_workflow` | string | Yes* | 検証の基盤となるComfyUIワークフロー（APIフォーマット）への相対パス。`*sequence`ジョブでは省略可能な場合があります。 |
| `placeholders` | dict | No | `grid_search`でプロンプトテンプレート内のプレースホルダーを展開するために使用するキーと値（リスト）の辞書。 |
| `fixed_parameters`| list | No | ジョブ内の全ての画像生成で共通して適用される固定パラメータのリスト。 |

**`fixed_parameters`の要素の構造:**
```yaml
- node_id: <ノードID>
  input_name: <入力名>
  value: <固定したい値>
```

---

### 2. `job_type: "grid_search"` の詳細

複数のパラメータ軸の全組み合わせ（デカルト積）を網羅的に検証するためのジョブタイプです。LoRAの比較やパラメータ間の相互作用の調査に最適です。

#### `grid_search` 専用キー

| キー | 型 | 必須 | 説明 |
| :--- | :--- | :--- | :--- |
| `variables` | list | Yes | 変化させるパラメータ軸のリスト。このリストに含まれる全変数の全組み合わせが実行されます。 |

**`variables`の要素の構造:**
```yaml
- node_id: <ノードID>
  input_name: <入力名>
  values:
    - <値1>
    - <値2>
    - ...
```

#### `grid_search` の設定例
```yaml
job_type: "grid_search"
job_name: "lora_vs_cfg_scale_grid_test"
base_workflow: "./workflows/base.json"

placeholders:
  composition: ["close-up", "full body"]

fixed_parameters:
  - {node_id: 171, input_name: "seed", value: 12345}

variables:
  # 軸1: プロンプト（プレースホルダーとワイルドカードを含む）
  - node_id: 149
    input_name: "text"
    values:
      - "<preset:quality>, 1girl, __hair_color__, {composition}"
  
  # 軸2: LoRAの重み
  - node_id: 116
    input_name: "model_weight_1"
    values: [0.6, 0.8, 1.0]

  # 軸3: CFGスケール
  - node_id: 171
    input_name: "cfg"
    values: [5.0, 7.0]
```
*   **実行内容**: 上記の例では、`composition`が2種類に展開され、`variables`は内部的に3軸（プロンプト2種、重み3種、CFG2種）となります。合計 2 x 3 x 2 = 12枚の画像が生成されます。各生成で`__hair_color__`はランダムに選択されます。

---

### 3. `job_type: "sequence"` の詳細

設定リストに定義されたプロンプトやパラメータを、上から順に1回ずつ実行します。特定のテーマに沿った画像を複数枚生成する「バッチ処理」や、アイデア出しに適しています。

#### `sequence` 専用キー

| キー | 型 | 必須 | 説明 |
| :--- | :--- | :--- | :--- |
| `prompts` | list | Yes | 実行したいプロンプトテンプレートのリスト。各要素で実行回数を指定できます。 |
| `prompt_target`| dict | Yes | `prompts`で解決されたプロンプト文字列を、どのノードのどの入力に適用するかを指定します。 |
| `random_parameters`| list | No | 実行ごとにランダムな値を生成して適用するパラメータのリスト。多様性を出すために使用します。 |
| `iterators`| dict | No | プロンプト内で順次選択する要素のリスト定義。`$[iterator_name]`記法で参照します。 |
| `default_runs`| int | No | プロンプトで`runs`が未指定の場合のデフォルト実行回数。 |

**`prompts`の要素の構造:**
```yaml
- template: <プロンプトテンプレート文字列>
  runs: <このテンプレートでの実行回数 (省略時は1)>
```

**`prompt_target`の構造:**
```yaml
prompt_target:
  node_id: <ノードID>
  input_name: <入力名>
```

**`random_parameters`の要素の構造:**
```yaml
- node_id: <ノードID>
  input_name: <入力名>
  type: <"int" または "choice">
  # typeが"int"の場合
  range: [<最小値>, <最大値>]
  # typeが"choice"の場合
  values: [<選択肢1>, <選択肢2>, ...]
```

#### `sequence` の設定例（v2.6新機能対応）
```yaml
job_type: "sequence"
job_name: "random_character_batch"
base_workflow: "./workflows/base.json"

# プロンプトを適用する場所を指定
prompt_target:
  node_id: 149
  input_name: "text"

# デフォルトrun数（省略時は1）
default_runs: 1

# 実行ごとにランダムな値を適用
random_parameters:
  - {node_id: 171, input_name: "seed", type: "int", range: [0, 999999999]}
  - {node_id: 116, input_name: "model_weight_1", type: "choice", values: [0.6, 0.7, 0.8]}

# 実行するプロンプトのリスト（新形式対応）
prompts:
  # 新形式1: リスト記法（ブロックスタイル）
  - - "<preset:quality>"
    - "1girl"
    - "<preset:characters/base>"
    - "in a cafe"
  
  # 新形式2: リスト記法（フロースタイル）
  - ["<preset:quality>", "1boy", "serious face", "__hair_color__", "in a library"]
  
  # 従来形式（個別runs指定）
  - template: "<preset:quality>, 1girl, special scene"
    runs: 3
```
*   **実行内容**: 上記の例では、最初の2つのプロンプトでdefault_runs分（1回ずつ）、最後のプロンプトで3回、合計5枚の画像が生成されます。各生成で、シード値はランダム、LoRAの重みは`[0.6, 0.7, 0.8]`からランダムに選ばれます。
*   **新機能**: v2.6より、プロンプトを複数行（要素）で記述できるリスト記法をサポート。従来のtemplate形式との混在も可能。

#### `sequence` のIterator機能（v2.7新機能）

プロンプト内で特定の要素を順次（シーケンシャル）に変化させるIterator機能を提供します。ランダム選択ではなく、決定論的な順番でプロンプトの一部を置き換えることができます。

**`iterators`の構造:**
```yaml
iterators:
  # 方法1: 手動でリスト定義
  <iterator_name>:
    - <値1>
    - <値2>
    - <値3>
  
  # 方法2: プリセットからグループを自動展開
  <iterator_name>:
    expand_preset: <プリセット名>
```

**使用方法:**
プロンプト内で`$[iterator_name]`記法を使用してIteratorを参照します。

**巡回ロジック:**
実行回数がIteratorの要素数を超える場合、リストの先頭に戻って巡回します（`index % len(iterator_list)`）。

**Iterator機能付きの設定例:**
```yaml
job_type: "sequence"
job_name: "iterator_example"
base_workflow: "./workflows/base.json"

prompt_target:
  node_id: 149
  input_name: "text"

# Iterator定義
iterators:
  # 手動リスト
  location:
    - "in a library"
    - "in a cafe"
    - "at a futuristic spaceport"
  
  # プリセット展開（expressionプリセットの全グループを使用）
  expression:
    expand_preset: "expression"

# Iteratorを使用したプロンプト
prompts:
  - template: "<preset:quality>, 1girl, $[expression], $[location]"
    runs: 8  # locationが3要素、expressionがN要素の場合、巡回で実行
```

**動作例:**
- location: 3要素、expression: 2要素（例）の場合、8回実行すると：
  - 1回目: expression[0], location[0]
  - 2回目: expression[1], location[1] 
  - 3回目: expression[0], location[2] (expressionが巡回)
  - 4回目: expression[1], location[0] (locationが巡回)
  - 5回目: expression[0], location[1]
  - ...




### ComfyV プロンプト・実行制御機能 仕様書

#### 1. Preset (`<preset:...>`) - 静的な部品化

*   **目的**: 頻繁に使うプロンプトの塊（コンポーネント）を、再利用可能な名前付きの部品として定義する。プロンプトの一貫性を保ち、メンテナンス性を向上させる。
*   **性質**: **決定論的（Deterministic）**。呼び出されると、定義された全てのタグがそのまま展開される。
*   **定義場所**: `prompts/presets/` ディレクトリ内の `.yaml` ファイル。
*   **キーの命名**: ディレクトリ構造を含む相対パス（例: `quality`, `characters/base`）。
*   **書き方 (定義)**: YAMLファイル内にタグのリストを記述。
    ```yaml
    # prompts/presets/quality.yaml
    - masterpiece
    - best quality
    ```
*   **書き方 (呼び出し)**: `<preset:キー>` の形式でプロンプトテンプレート内に記述。
    ```yaml
    # config.yaml
    template: "<preset:quality>, 1girl, ..."
    ```
*   **v2.2高度な演算**: 同一プリセット内でのグループ演算をサポート。
    ```yaml
    # 許可される演算
    <preset:quality#base+hdr-unwanted>  # baseとhdrを結合、unwantedを除去
    
    # 禁止される演算（エラー）
    <preset:quality+style#anime>        # 異なるプリセット間演算は未定義
    ```
*   **ファイル階層**: `character/akira`形式のファイル階層はサポート済み。Preset内から他のPresetを呼び出す再帰処理も可能。
*   **グループ階層**: `#style.anime`形式のグループ内ドット記法は未サポート。`#style_anime`形式のアンダースコア記法を使用。
*   **主な用途**: 品質向上タグ、キャラクターの基本設定、ネガティブプロンプトの共通部分など、常に含めたい決まり文句のグループ化。

---

#### 2. Wildcard (`__wildcard__`) - ランダムな多様性

*   **目的**: プロンプトにランダムな要素を注入し、生成結果の多様性を生み出す。
*   **性質**: **非決定的（Non-deterministic）**。呼び出されるたびに、定義されたリストから要素が**1つだけランダムに選択**されて置換される。
*   **定義場所**: `prompts/wildcards/` ディレクトリ内の `.txt` ファイル。
*   **キーの命名**: ディレクトリ構造を含む相対パス（例: `hair_color`, `locations/city`）。
*   **書き方 (定義)**: TXTファイル内に、1行に1つの選択肢を記述。
    ```txt
    # prompts/wildcards/hair_color.txt
    blonde hair
    black hair
    brown hair
    ```
*   **書き方 (呼び出し)**: `__キー__` の形式でプロンプトテンプレート内に記述。
    ```yaml
    # config.yaml
    template: "1girl, __hair_color__, ..."
    ```
*   **主な用途**: 髪の色、目の色、服装、ポーズ、背景など、バリエーションを持たせたい要素。

---

#### 3. Placeholder (`{placeholder}`) - 体系的な組み合わせの生成

*   **目的**: `grid_search`ジョブにおいて、プロンプトテンプレートの一部を複数の値で体系的に置き換え、組み合わせの次元を増やす。
*   **性質**: **決定論的（Deterministic）**。`GridSearchJobExecutor`がジョブ実行前に、定義された全ての値の組み合わせにプロンプトテンプレートを展開する。
*   **定義場所**: `config.yaml`内の`placeholders`セクション。
*   **キーの命名**: `placeholders`セクションで定義したキー名。
*   **書き方 (定義)**:
    ```yaml
    # config.yaml
    placeholders:
      composition: ["close-up", "full body"]
      style: ["<preset:styles/anime>", "<preset:styles/photorealistic>"]
    ```
*   **書き方 (呼び出し)**: `{キー}` の形式で、`grid_search`ジョブの`variables`内のプロンプトテンプレート文字列に記述。
    ```yaml
    # config.yaml (variablesセクション)
    - node_id: 149
      input_name: "text"
      values:
        - "1girl, {composition}, {style}"
    ```
*   **主な用途**: 構図、画風、キャラクターの服装など、他のパラメータ（LoRAの重みなど）と掛け合わせて網羅的に比較検証したい要素。

---

#### 4. Iterator (`variables` in `grid_search`) - 実行ループの主軸

*   **目的**: `grid_search`ジョブの実行ループを駆動する主軸。ここに定義されたパラメータの全組み合わせ（デカルト積）が、生成される画像の全パターンとなる。
*   **性質**: **決定論的（Deterministic）**。`JobExecutor`が`itertools.product`を使い、定義された全ての`values`の組み合わせを生成する。
*   **定義場所**: `config.yaml`内の`variables`セクション。
*   **キーの命名**: `node_id`と`input_name`で直接ターゲットを指定。
*   **書き方 (定義)**:
    ```yaml
    # config.yaml
    variables:
      - node_id: 116
        input_name: "model_weight_1"
        values: [0.6, 0.8]
      - node_id: 171
        input_name: "cfg"
        values: [5.0, 7.0]
    ```
*   **主な用途**: 検証の主軸となるパラメータ（LoRAの重み、CFGスケール、サンプラー名など）。プロンプト自体を軸にすることも可能。

---

### 解決・実行の順序と相互作用

これらの機能は、以下の順序で解決・実行されます。

1.  **`GridSearchJobExecutor`の事前処理 (`_preprocess_variables`)**:
    *   `variables` 内のプロンプトテンプレートをスキャンする。
    *   `{placeholder}` を見つけ、`placeholders`セクションの定義に基づいて、プロンプトテンプレートの**全組み合わせ**を生成する。この時点で、`variables`の次元が内部的に増加する。

2.  **`GridSearchJobExecutor`の実行ループ (`run`)**:
    *   事前処理済みの `variables` から、`itertools.product` を使って**Iterator**の全組み合わせを生成する。これがメインの実行ループとなる。

3.  **ループ内の`PromptResolver`の実行**:
    *   ループの各イテレーションで、現在の組み合わせからプロンプトテンプレートが取り出される。
    *   `prompt_resolver.resolve()` が呼び出される（v2.2では6ステージパイプライン）。
        a.  **① Parse**: テンプレートをAST（Text, PresetExpr, Placeholder, Wildcard）に解析
        b.  **② PresetEval**: `<preset:..>` を**再帰的に展開**し、グループ演算を処理
        c.  **③ Placeholder**: `{placeholder}` を値に置換（PlaceholderSubstitutor完全実装）
        d.  **④ Wildcard**: `__wildcard__` を**ランダムに置換**（WildcardSubstitutor完全実装：再パース機能対応、sampleモード完全実装）
        e.  **⑤ Filter**: TagSetを統合、ignore_tags適用（TagFilter完全実装：高性能化・再パース統合）
        f.  **⑥ Format**: 最終文字列に整形（PromptFormatter完全実装：locale対応・将来拡張準備・包括的テスト）

この多段階の解決プロセスにより、**「体系的（Placeholder, Iterator）」**でありながら**「再利用可能（Preset）」**で、かつ**「多様性を持つ（Wildcard）」**という、非常に強力で柔軟なプロンプト生成とジョブ実行が可能になっています。