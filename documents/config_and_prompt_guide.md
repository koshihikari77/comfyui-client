# ComfyV 設定ファイル & プロンプト記法ガイド

このドキュメントは **設定ファイル（YAML）** と **プロンプト（テンプレート）記法** に絞った実用ガイドです。  
設計書（`documents/design_and_specification.md`）の要点に加え、**現行実装の制約/注意点**も併記します。

---

## 1. 設定ファイルの全体像

ComfyVは通常、次の2ファイルを読みます。

- **接続設定**: `configs/connection_config.yaml`
- **ジョブ設定**: `configs/jobs/*.yaml`（任意のパスを `--job-config` で指定）

### 1.1 接続設定（connection_config.yaml）

最小構成:

```yaml
server_address: "127.0.0.1:8188"
```

#### 注意（現行実装）
- `server_address` は **`host:port`** と **`http(s)://host:port`** の両方に対応しています（`core/api_client.py` で正規化）。
  - 例: `127.0.0.1:8188`（推奨）
  - 例: `http://localhost:8188`
  - 例: `https://example.com:8188`

---

## 2. ジョブ設定（job-config YAML）

ジョブ設定には `job_type` に応じたセクションがあります。

### 2.1 共通キー

```yaml
job_name: "my_job_name"
job_type: "grid_search"  # または "sequence"
base_workflow: "workflows/api_base.json"  # grid_searchでは必須（sequenceでも使うことが多い）
```

#### base_workflow のパス解決ルール（現行実装）
- `configs/jobs/**/xxx.yaml` の場合、`configs/` を基準に相対パス解決します。
  - `base_workflow: "workflows/api_base.json"` → `configs/workflows/api_base.json`

---

## 3. GridSearch（job_type: grid_search）

複数軸の **全組み合わせ（デカルト積）** を実行します。

### 3.1 最小例

```yaml
job_name: "lora_grid"
job_type: "grid_search"
base_workflow: "workflows/api_base.json"

variables:
  - node_id: 149
    input_name: "text"
    values:
      - "<preset:quality#default>, 1girl, __hair_color__"
      - "<preset:quality#default>, 1girl, __eye_color__"

  - node_id: 171
    input_name: "cfg"
    values: [5.0, 7.0]
```

### 3.2 placeholders（プレースホルダー展開）

```yaml
placeholders:
  composition: ["close-up", "full body"]
```

```yaml
variables:
  - node_id: 149
    input_name: "text"
    values:
      - "1girl, {composition}, __hair_color__"
```

#### 注意（現行実装）
- GridSearchでは、`variables` のうち **input_name に `text` を含む**ものだけを対象に、`{...}` を **事前展開**します（`core/executors/grid_search_executor.py`）。
- 展開後に `itertools.product` で全組み合わせを作るため、`placeholders` が多いと実行数が爆発します。

---

## 4. Sequence（job_type: sequence）

定義されたプロンプトを **上から順に** 実行します。  
さらに、**Constant（%...%）** と **Iterator（$[...]）** による前処理が入ります。

### 4.1 最小例

```yaml
job_name: "sequence_demo"
job_type: "sequence"
base_workflow: "workflows/api_base.json"

# 解決済みプロンプトを適用する先（Sequenceではほぼ必須）
prompt_target:
  node_id: 149
  input_name: "text"

prompts:
  - template: "1girl, <preset:quality#default>, __hair_color__"
    runs: 3
```

### 4.2 新しいプロンプト形式（リスト記法）

次のように `List[str]` でも書けます（内部で `", "` 結合して template 化）。

```yaml
prompts:
  - ["%base_quality%", "1girl", "$[expression]", "$[location]"]
  - ["%base_quality%", "1boy", "serious"]
```

### 4.3 constants（%...%）

```yaml
constants:
  base_quality: "masterpiece, best quality"

prompts:
  - template: "%base_quality%, 1girl, __hair_color__"
    runs: 2
```

定数の値は **文字列（str）** または **リスト（List[str]）** を指定できます。リストの場合はテンプレート置換時に `", ".join(list)` で結合されます。

```yaml
constants:
  tags: ["masterpiece", "best quality", "1girl"]

prompts:
  - template: "%tags%, standing"
    runs: 1
# → "masterpiece, best quality, 1girl, standing"
```

#### 制約（現行実装）
- 定数名は正規表現 `([a-zA-Z_][a-zA-Z0-9_]*)` に一致する必要があります。
  - OK: `%base_quality%`
  - NG: `%base-quality%` / `%base/quality%`

### 4.4 iterators（$[...]）

手動リスト:

```yaml
iterators:
  location: ["library", "cafe", "spaceport"]

prompts:
  - template: "1girl, $[location]"
    runs: 5
```

expand_preset（プリセットのグループ名を列挙して `<preset:xxx#group>` を巡回）:

```yaml
iterators:
  expression:
    expand_preset: "expression"
```

#### 制約（現行実装）
- Iterator名は正規表現 `([a-zA-Z_][a-zA-Z0-9_]*)` に一致する必要があります。

### 4.5 fixed/random/parameter_combinations（パラメータ適用）

固定（最低優先度）:

```yaml
fixed_parameters:
  - { node_id: 171, input_name: "seed", value: 42 }
```

ランダム（中優先度）:

```yaml
random_parameters:
  - { node_id: 171, input_name: "seed", type: "int", range: [0, 999999999] }
  - { node_id: 116, input_name: "model_weight_1", type: "choice", values: [0.6, 0.8] }
```

組み合わせ（最高優先度・巡回適用）:

```yaml
parameter_combinations:
  - name: "combo1"
    parameters:
      - { node_id: 171, input_name: "steps", value: 20 }
      - { node_id: 171, input_name: "cfg", value: 6.0 }
  - name: "combo2"
    parameters:
      - { node_id: 171, input_name: "steps", value: 30 }
      - { node_id: 171, input_name: "cfg", value: 7.0 }
```

#### 適用優先度（現行実装）
`parameter_combinations > random_parameters > fixed_parameters`

---

## 5. プロンプト（テンプレート）記法

ComfyVの「プロンプト」は、単なる文字列ではなく、記法を含む **テンプレート**です。  
（GridSearchの `variables[].values`、Sequenceの `prompts[].template` が主な入力箇所）

### 5.1 記法一覧

- **Preset**: `<preset:...>`
- **Placeholder**: `{name}`
- **Wildcard**: `__name__`
- **Constant**（Sequence前処理）: `%name%`
- **Iterator**（Sequence前処理）: `$[name]`

### 5.2 処理順序

Sequenceの場合:

```
Template
  → Constant置換（%...%）
  → Iterator置換（$[...]）
  → Parse
  → Preset
  → Placeholder
  → Wildcard
  → Filter（ignore_tags）
  → Format（locale）
```

GridSearchの場合:
- 事前に `{...}` を展開（対象は input_name が text 系の変数のみ）
- その後、各値（文字列）に対して `PromptResolverV2.resolve()` を実行

---

## 6. 各記法の詳細

### 6.1 Preset（<preset:...>）

基本:
- `<preset:quality>`（全グループの和集合）
- `<preset:quality#default>`（defaultグループのみ）

演算:
- `<preset:quality#base+hdr-unwanted>`
  - `+` は和集合、`-` は差集合
  - **同一プリセット内のみ**（クロスプリセット演算はエラー扱い）

階層（ファイル階層を `/` で表現）:
- `<preset:character/akira#base>`

### 6.2 Placeholder（{name}）

`placeholders:` に定義した値から置換します。
- sample（通常）: ランダムに1つ選択
- expand（GridSearch前処理など）: 全組み合わせ展開

### 6.3 Wildcard（__name__）

`configs/prompts/wildcards/*.txt` からランダムに1行選びます。  
階層も使えます（例: `configs/prompts/wildcards/clothes/top.txt` → `__clothes/top__`）。

### 6.4 Constant（%name%）※Sequenceのみ

`constants:` で定義した文字列を、テンプレート内の `%name%` に差し込みます。

### 6.5 Iterator（$[name]）※Sequenceのみ

`iterators:` のリストを `iteration_index % len(list)` で巡回して差し込みます。

---

## 7. scene_delta（差分ベースプロンプト記述）※Sequenceのみ

長いプロンプトを差分で記述できる拡張記法です。シーンごとの変更点だけを書くことで、可読性と保守性を向上させます。  
**注意**: 旧キー `prompts_delta` は廃止されています。`scene_delta` を使用してください。

### 7.1 基本構造

```yaml
prompt_template:
  order: [quality, subject, action, location, extra]  # 出力順
  slots:
    quality: "masterpiece, best quality"
    subject: "1girl"
    action: null       # null = 未設定
    location: null
    extra: []          # 配列も可

scene_delta:
  - { location: "bedroom" }
  - { action: "standing" }
  - { location: "kitchen", action: "cooking" }
```

**動作**:
- 各行は直前の状態を継承し、指定したslotだけ上書き
- `order` の順にフラット化して `prompts` を生成

**出力される prompts**:
```
1. "masterpiece, best quality, 1girl, bedroom"
2. "masterpiece, best quality, 1girl, standing, bedroom"
3. "masterpiece, best quality, 1girl, cooking, kitchen"
```

### 7.2 予約キー

通常のslot指定に加え、以下の予約キー（`_` 始まり）が使えます：

| キー | 説明 | 例 |
|------|------|-----|
| `_id` | このシーンのID（参照用） | `_id: scene_a` |
| `_from` | 継承元（`base` or ID） | `_from: base` |
| `_unset` | slotを出力から除外 | `_unset: [action]` |
| `_add` | slotにタグを追加（str はカンマ区切りで分割して追加） | `_add: {extra: "tag"}` |
| `_del` | slotからタグを完全一致で削除（存在しないタグは無視） | `_del: {extra: "tag"}` |
| `_runs` | このpromptのruns指定 | `_runs: 3` |
| `_name` | prompt名 | `_name: "scene1"` |
| `_params` | ワークフローパラメータ（set→以後継承） | `_params: [{node_id: 10, input_name: "width", value: 768}]` |

### 7.3 継承と参照

```yaml
scene_delta:
  - { _id: "intro", action: "standing", location: "park" }
  - { action: "walking" }                     # 直前（intro）を継承
  - { _from: "intro", location: "beach" }     # introを参照してlocationだけ変更
  - { _from: "base", action: "sleeping" }     # テンプレートにリセット
```

### 7.4 配列slotへの追加

```yaml
prompt_template:
  order: [subject, details]
  slots:
    subject: "1girl"
    details: []

scene_delta:
  - { _add: { details: "blue eyes" } }
  - { _add: { details: ["blonde hair", "smile"] } }  # 累積される
```

**出力**:
```
1. "1girl, blue eyes"
2. "1girl, blue eyes, blonde hair, smile"
```

### 7.5 slotの除外

```yaml
scene_delta:
  - { action: "running" }
  - { _unset: [action] }  # actionを出力から除外
```

### 7.6 よくある運用メモ（現行実装）

- **`_add` は累積**します  
  各シーンは「直前stateを継承→差分適用」なので、`_add` で入れたタグは **消さない限り残り続けます**。戻したい場合は次のいずれかを使います。
  - **setで上書き**: `clothing_lower: "%char_clothing_lower%"`
  - **`_del` で削除**（完全一致）
  - **`_unset` でslotごと消す**
  - **`_from: base`** でテンプレート状態にリセット

- **`%constant%` は scene_delta コンパイル時にも展開されます**  
  `prompt_template.slots` や `scene_delta` の set / `_add` / `_del` に `%name%` を書けます。  
  これにより、`%...%` を含むslotでも **展開後のタグに対して `_del` が効く**ようになっています。

- **`order` の “区切り” を出したい場合は slot を用意します**  
  `order` に `break` を入れるだけでは何も出ません（そのslotが未定義ならスキップされるため）。  
  出力に `BREAK` を混ぜたい場合は、例えば `slots.break: ["BREAK"]` を用意して `order` に `break` を入れます。

- **`order` に同じslot名を複数回入れると、その回数ぶん重複して出力されます**

- **`_params` でワークフローパラメータをシーン単位で変更できます（set→以後継承）**  
  `_params: [{node_id: 10, input_name: "width", value: 768}, ...]` のように指定すると、そのシーン以降でその値が継承されます。  
  実行時のパラメータ優先度は **scene_delta params が fixed/random/parameter_combinations より優先**され、**prompt_target（プロンプトテキスト）は最後に適用**されます。

### 7.7 制約

- `prompts` と `scene_delta` は **同時に指定できません**（エラーになります）
- `scene_delta` を使う場合は `prompt_template` が必須です
- `_from` で存在しないIDを参照するとエラーになります
- **`prompts_delta` は廃止されています**。`scene_delta` を使用してください（指定するとエラーになります）

---

## 8. エスケープ

テンプレート中で構文文字をそのまま使いたい場合:
- `\<` → `<`
- `\{` → `{`
- `\__` → `__`

---

## 9. 注意（現行実装と設計書の差）

このガイドは「書ける」ことに寄せていますが、現行コードでは次が未配線/制約になっています。

- **PromptResolver設定（ignore_tags / ignore_groups / locale / strict_level / seed）**は、ジョブYAMLに書いても実行時に反映されない場合があります（DI側が `Config` プロパティを参照するため）。
- **node_id をノード名で書く（例: `"VAEデコード"`）**は設計思想として存在し、WorkflowLoaderも対応していますが、Pydanticスキーマが `int` 前提のため、ジョブYAMLの多くの箇所は現状 **数値ID推奨**です。

