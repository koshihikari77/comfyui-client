# ComfyV 設定ファイル & プロンプト記法ガイド

このドキュメントは **設定ファイル（YAML）** と **プロンプト（テンプレート）記法** に絞った実用ガイドです。  
設計書（`documents/design_and_specification.md`）の要点に加え、**現行実装の制約/注意点**も併記します。

> **書き方の基本方針**: 新規ジョブは **`job_type: sequence` + `scene_delta`（差分ベース）** で書きます（→ §3）。  
> 従来形式（Sequence の `prompts` フラット記法・`grid_search`）は **§8「従来の書き方（レガシー）」** にまとめてあります。動きますが新規では推奨しません。

---

## 1. 設定ファイルの全体像

ComfyVは通常、次の2ファイルを読みます。

- **接続設定**: `configs/connection_config.yaml`
- **ジョブ設定**: `configs/jobs/*.yaml`（`comfyv run <job_config.yaml>` の位置引数で指定）

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
job_type: "sequence"     # 基本は sequence。従来形式の grid_search は §8
base_workflow: "workflows/api_base.json"
```

#### base_workflow のパス解決ルール（現行実装）
- `configs/jobs/**/xxx.yaml` の場合、`configs/` を基準に相対パス解決します。
  - `base_workflow: "workflows/api_base.json"` → `configs/workflows/api_base.json`
- 案件ディレクトリ配下など `configs/` の外に置く場合は **絶対パス**で指定します。

---

## 3. Sequence（job_type: sequence）— 基本形は scene_delta

定義したシーンを **上から順に** 実行します。さらに **Constant（%...%）** と **Iterator（$[...]）** による前処理が入ります。

**基本形は `scene_delta`**（差分ベースプロンプト記述）です。長いプロンプトを「シーンごとの変更点だけ」で書けるので可読性・保守性が高く、`--scenes` による部分実行（§3.10）にも対応します。  
旧来の `prompts` フラット記法は §8.1（従来の書き方）に置いています。

> **注意**: `prompts` と `scene_delta` は **同時に指定できません**。`scene_delta` を使う場合は `prompt_template` が必須です。旧キー `prompts_delta` は廃止されています。

### 3.1 最小例（scene_delta）

```yaml
job_name: "sequence_demo"
job_type: "sequence"
base_workflow: "workflows/api_base.json"

# 解決済みプロンプトを適用する先（Sequenceでは必須）
prompt_target:
  node_id: 149
  input_name: "text"

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
- `order` の順にフラット化して内部の `prompts` を生成

**生成されるプロンプト**:
```
1. "masterpiece, best quality, 1girl, bedroom"
2. "masterpiece, best quality, 1girl, standing, bedroom"
3. "masterpiece, best quality, 1girl, cooking, kitchen"
```

### 3.2 継承と参照

```yaml
scene_delta:
  - { _id: "intro", action: "standing", location: "park" }
  - { action: "walking" }                     # 直前（intro）を継承
  - { _from: "intro", location: "beach" }     # introを参照してlocationだけ変更
  - { _from: "base", action: "sleeping" }     # テンプレートにリセット
```

### 3.3 予約キー

通常のslot指定に加え、以下の予約キー（`_` 始まり）が使えます：

| キー | 説明 | 例 |
|------|------|-----|
| `_id` | このシーンのID（参照用・`--scenes` の指定にも使える） | `_id: scene_a` |
| `_from` | 継承元（`base` or ID） | `_from: base` |
| `_unset` | slotの値を None にして出力から除外（以後継承） | `_unset: [action]` |
| `_invisible` | slotの値は維持し、出力からだけ除外（以後継承） | `_invisible: [lighting]` |
| `_visible` | slotを再び出力対象に戻す（以後継承） | `_visible: [lighting]` |
| `_add` | slotにタグを追加（str はカンマ区切りで分割して追加） | `_add: {extra: "tag"}` |
| `_del` | slotからタグを完全一致で削除（存在しないタグは無視） | `_del: {extra: "tag"}` |
| `_runs` | このシーンのruns指定 | `_runs: 3` |
| `_name` | シーン名 | `_name: "scene1"` |
| `_params` | ワークフローパラメータ（set→以後継承） | `_params: [{node_id: 10, input_name: "width", value: 768}]` |

### 3.4 配列slotへの追加（_add / _del と +/- 記法）

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

**slot の `+` / `-` 記法（_add / _del の省略記法）**  
通常の slot 指定で、値の**先頭が `+` なら追加**、**`-` なら削除**として扱えます。`_add` / `_del` と同一シーン内で混在可能です。値はダブルクォートで囲むだけでよく、外側のクォートは不要です。

- `slot: "+tag"` または `slot: "+tag1, tag2"` → その slot に追加（`_add: { slot: "tag" }` と同じ）
- `slot: "-tag"` または `slot: "-tag1, tag2"` → その slot から完全一致で削除（`_del: { slot: "tag" }` と同じ）

```yaml
prompt_template:
  order: [subject, pose]
  slots:
    subject: "1girl"
    pose: "standing"

scene_delta:
  - { pose: "+hand up" }   # pose に "hand up" を追加
  - { pose: "-standing" }  # pose から "standing" を削除
```

### 3.5 slotの除外・非表示

- **`_unset`**: slotの**値**を None にし、出力からも除外する。以後のシーンでもその slot は「無い」状態が継承される。
- **`_invisible`** / **`_visible`**: slotの**値は維持**したまま、出力に含めるかどうかだけを切り替える。  
  - `_invisible: [slot名]` で出力から隠し、`_visible: [slot名]` で再表示。  
  - 非表示の間に set / _add / _del で値を変えておくと、`_visible` で再表示したときに更新後の値が出力される。  
  - `_from` で参照するときは、**値state と 可視state の両方**が引き継がれる。

```yaml
scene_delta:
  - { action: "running" }
  - { _unset: [action] }  # action の値も出力も消す
  - { _invisible: [lighting] }  # lighting の値は維持、出力からだけ隠す
  - { _visible: [lighting] }   # 再表示（その時点の値が出力される）
```

### 3.6 default_runs（ジョブ全体のデフォルト実行回数）と _runs

ジョブのトップレベルで **`default_runs`** を指定すると、各シーンで `_runs` を書いていない場合に、その回数が使われます。デフォルトは `1` です。

**runs は「そのシーンで生成する枚数」の上限**です。テンプレートに `{name}`（直積）が含まれる場合、組み合わせ数を超える run では cycle（`run_index % 組み合わせ数`）で同じ組み合わせ列を繰り返します。詳細は **§5.2 Placeholder** を参照してください。

```yaml
default_runs: 2
scene_delta:
  - { subject: "1girl" }              # 2回実行（default_runs）
  - { subject: "1boy", _runs: 3 }     # 3回実行（明示指定が優先）
```

### 3.7 constants（%...%）

`constants:` で定義した値を、slot や scene_delta 内の `%name%` に差し込みます。

```yaml
constants:
  base_quality: "masterpiece, best quality"

prompt_template:
  order: [quality, subject]
  slots:
    quality: "%base_quality%"
    subject: "1girl"

scene_delta:
  - { subject: "1girl, __hair_color__" }
```

定数の値は **文字列（str）** または **リスト（List[str]）** を指定できます。リストの場合はテンプレート置換時に `", ".join(list)` で結合されます。

```yaml
constants:
  tags: ["masterpiece", "best quality", "1girl"]
# %tags% → "masterpiece, best quality, 1girl"
```

#### 制約（現行実装）
- 定数名は正規表現 `([a-zA-Z_][a-zA-Z0-9_]*)` に一致する必要があります。
  - OK: `%base_quality%`
  - NG: `%base-quality%` / `%base/quality%`
- `%constant%` は **scene_delta コンパイル時にも展開**されます。`prompt_template.slots` や scene_delta の set / `_add` / `_del` に書けます。これにより `%...%` を含む slot でも、展開後のタグに対して `_del` が効きます。

### 3.8 iterators（$[...]）

`iterators:` のリストを `iteration_index % len(list)` で巡回して `$[name]` に差し込みます。

手動リスト:

```yaml
iterators:
  location: ["library", "cafe", "spaceport"]

scene_delta:
  - { location: "$[location]" }
  - { location: "$[location]" }
  - { location: "$[location]" }
```

expand_preset（プリセットのグループ名を列挙して `<preset:xxx#group>` を巡回）:

```yaml
iterators:
  expression:
    expand_preset: "expression"
```

#### 制約（現行実装）
- Iterator名は正規表現 `([a-zA-Z_][a-zA-Z0-9_]*)` に一致する必要があります。

### 3.9 fixed/random/parameter_combinations（パラメータ適用）

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
`scene_delta の _params > parameter_combinations > random_parameters > fixed_parameters`  
なお **prompt_target（プロンプトテキスト）は最後に適用**されます。

### 3.10 部分実行（CLI: --scenes）

`scene_delta` の **ID / index / 範囲** を指定して、そのシーンだけ実行できます。  
**runs/iterator で増える「画像単位の指定」はできません**（選択したシーンは通常どおり runs 分実行されます）。

```bash
# index 指定
uv run comfyv run "configs/jobs/xxx.yaml" --scenes "0,2"

# ID 指定
uv run comfyv run "configs/jobs/xxx.yaml" --scenes "base_sitting,teasing_chest_show"

# 範囲指定（両端含む）
uv run comfyv run "configs/jobs/xxx.yaml" --scenes "3-7"

# ここから最後まで（開始のみ）
uv run comfyv run "configs/jobs/xxx.yaml" --scenes "6-"
uv run comfyv run "configs/jobs/xxx.yaml" --scenes "base_sitting-"

# 先頭からここまで（終了のみ）
uv run comfyv run "configs/jobs/xxx.yaml" --scenes "-6"
uv run comfyv run "configs/jobs/xxx.yaml" --scenes "-base_sitting"

# 複合指定
uv run comfyv run "configs/jobs/xxx.yaml" --scenes "0,2,base_sitting,5-12"
```

**注意**:
- `--scenes` は **scene_delta がある sequence ジョブ専用**です（`prompts` フラット形式や grid_search ではエラー）。
- 指定したシーンの **実行順は index 昇順**になります。

### 3.11 よくある運用メモ（現行実装）

- **`_add` は累積**します  
  各シーンは「直前stateを継承→差分適用」なので、`_add` で入れたタグは **消さない限り残り続けます**。戻したい場合は次のいずれかを使います。
  - **setで上書き**: `clothing_lower: "%char_clothing_lower%"`
  - **`_del` で削除**（完全一致）
  - **`_unset` でslotごと消す**
  - **`_from: base`** でテンプレート状態にリセット

- **`order` の “区切り” を出したい場合は slot を用意します**  
  `order` に `break` を入れるだけでは何も出ません（そのslotが未定義ならスキップされるため）。  
  出力に `BREAK` を混ぜたい場合は、例えば `slots.break: ["BREAK"]` を用意して `order` に `break` を入れます。

- **`order` に同じslot名を複数回入れると、その回数ぶん重複して出力されます**

- **`_params` でワークフローパラメータをシーン単位で変更できます（set→以後継承）**  
  `_params: [{node_id: 10, input_name: "width", value: 768}, ...]` のように指定すると、そのシーン以降でその値が継承されます（優先度は §3.9 参照）。

### 3.12 制約

- `prompts` と `scene_delta` は **同時に指定できません**（エラーになります）
- `scene_delta` を使う場合は `prompt_template` が必須です
- `_from` で存在しないIDを参照するとエラーになります
- **`prompts_delta` は廃止されています**。`scene_delta` を使用してください（指定するとエラーになります）

---

## 4. プロンプト（テンプレート）記法

ComfyVの「プロンプト」は、単なる文字列ではなく、記法を含む **テンプレート**です。  
（主な入力箇所: Sequence の `scene_delta` のslot値 / `prompt_template.slots`。従来形式では `prompts[].template`、GridSearch の `variables[].values` → §8）

### 4.1 記法一覧

- **Preset**: `<preset:...>`
- **Placeholder**: `{name}`（直積・デフォルト）/ `{name:r}`（ランダム）/ `{a | b | c}`（インライン直積）/ `{a | b:r}`（インラインランダム）
- **Wildcard**: `__name__`
- **Constant**（Sequence前処理）: `%name%`
- **Iterator**（Sequence前処理）: `$[name]`

### 4.2 処理順序

Sequenceの場合:

```
Template（scene_delta を order でフラット化したもの）
  → Constant置換（%...%）
  → Iterator置換（$[...]）
  → Inline placeholder 前処理（{a | b} → {_inline_N}）
  → Parse
  → Preset
  → Placeholder（外部参照 + インライン）
  → Wildcard
  → Filter（ignore_tags）
  → Format（locale）
```

（GridSearch の処理順序は §8.2 を参照）

---

## 5. 各記法の詳細

### 5.1 Preset（<preset:...>）

基本:
- `<preset:quality>`（全グループの和集合）
- `<preset:quality#default>`（defaultグループのみ）

演算:
- `<preset:quality#base+hdr-unwanted>`
  - `+` は和集合、`-` は差集合
  - **同一プリセット内のみ**（クロスプリセット演算はエラー扱い）

階層（ファイル階層を `/` で表現）:
- `<preset:character/akira#base>`

### 5.2 Placeholder（{name} / {name:r} / インライン）

`placeholders:` に定義した値から置換します。**同一テンプレート内で expand と sample を混在できます。**

#### 5.2.1 外部参照（placeholders: で定義）

| 記法 | 意味 | 用途 |
|------|------|------|
| `{name}` | **直積（expand）** — 組み合わせ列の n 番目を順に使用 | Sequence では run ごとに 0, 1, 2, … 番目の組み合わせを順に適用 |
| `{name:r}` | **ランダム（sample）** — 毎回ランダムに1つ選択 | 直積にしたくない slot だけ :r を付ける |

#### 5.2.2 インライン記法（テンプレート内に直接記述）

候補をテンプレート文字列の中に直接パイプ `|` 区切りで書けます。`placeholders:` での事前定義は不要です。

| 記法 | 意味 | 例 |
|------|------|-----|
| `{a \| b \| c}` | **直積（expand）** — 外部参照と同様に直積展開 | `{from side \| pov \| from above}` |
| `{a \| b \| c:r}` | **ランダム（sample）** — 毎回ランダムに1つ選択 | `{from side \| pov \| from above:r}` |
| `{a \| b \| }` | **空選択肢あり** — 末尾パイプで「何も出さない」を含む | `{hand up \| }` → "hand up" or 空 |

**判別ルール**: `{}` 内に `|` が含まれればインライン、なければ外部参照。

**使い分け**:
- 同じ候補リストを複数テンプレートで再利用 → 外部参照 `{name}`
- 1箇所だけで使い捨て → インライン `{a | b | c}`

```yaml
# インラインの例
scene_delta:
  - pose: "{from side | pov | from above}, {standing | sitting}"
    # → 3 x 2 = 6 通りの直積展開

  - expression: "{smile | blush | closed eyes:r}"
    # → 毎回ランダムに 1 つ選択
```

#### 5.2.3 ネスト（再パース）

Placeholder の値に `{name}` / `{name:r}` / `{a | b:r}` などのテンプレート構文が含まれている場合、**自動的に再パース**されて展開されます（最大15段）。`<preset:...>` や `__wildcard__` も同様に再パースされます。

これにより、placeholder 値の中にインライン placeholder を埋め込む**ネスト記法**が使えます。

```yaml
# 例: ベース色ごとに異なる装飾候補をインラインで持たせる
placeholders:
  color_scheme:
    - "black bra, black panties, {lace bra, (white trim:1.3) | (red trim:1.3):r}"
    - "white bra, white panties, {bow panties, pink bow | (pink trim:1.3):r}"
    - "red bra, red panties, {bow panties, white bow | (black trim:1.3):r}"
```

`{color_scheme:r}` を使うと、まずベース色がランダムに選ばれ、次にその値の中のインライン `{...:r}` が再パースされて装飾がランダムに選ばれます。

**制約**:
- 再パース深度は最大 20（`MAX_DEPTH`）
- 多段イテレーションは最大 15 回
- `{` `}` のネスト（`{{...}}`）は不可。インライン `{a | b}` の中にさらに `{c | d}` は書けない
- 外部参照 `{name}` やインライン `{a | b}` を placeholder 値の**文字列として**含める形でネストする

#### 5.2.4 Sequence での runs の扱い

- `runs`（scene_delta では `_runs`）は「そのシーンで生成する枚数」の**上限**です。  
- expand の組み合わせ数（comboCount）が runs より少ない場合は **cycle** します（`run_index % comboCount` で n を決める）。  
- 例: `{a}` が 2 候補・`{b}` が 3 候補 → comboCount=6。`_runs: 10` なら 0〜5 番目を順に使い、6〜9 回目は 0〜3 番目を再度使用。
- インラインの expand も外部参照と同じく直積に参加します。

**直積上限（placeholder_max_expansion）**  
- expand の組み合わせ数がこの値を超えるとエラーになります。  
- デフォルトは **128**。ジョブ設定や Resolver の config で `placeholder_max_expansion` を指定すると上書きできます。

### 5.3 Wildcard（__name__）

`configs/prompts/wildcards/*.txt` からランダムに1行選びます。  
階層も使えます（例: `configs/prompts/wildcards/clothes/top.txt` → `__clothes/top__`）。

### 5.4 Constant（%name%）※Sequenceのみ

`constants:` で定義した文字列を、テンプレート内の `%name%` に差し込みます（詳細は §3.7）。

### 5.5 Iterator（$[name]）※Sequenceのみ

`iterators:` のリストを `iteration_index % len(list)` で巡回して差し込みます（詳細は §3.8）。

---

## 6. エスケープ

テンプレート中で構文文字をそのまま使いたい場合:
- `\<` → `<`
- `\{` → `{`
- `\__` → `__`

---

## 7. 注意（現行実装と設計書の差）

このガイドは「書ける」ことに寄せていますが、現行コードでは次が未配線/制約になっています。

- **PromptResolver設定（ignore_tags / ignore_groups / locale / strict_level / seed）**は、ジョブYAMLに書いても実行時に反映されない場合があります（DI側が `Config` プロパティを参照するため）。
- **node_id をノード名で書く（例: `"VAEデコード"`）**は設計思想として存在し、WorkflowLoaderも対応していますが、Pydanticスキーマが `int` 前提のため、ジョブYAMLの多くの箇所は現状 **数値ID推奨**です。

---

## 8. 従来の書き方（レガシー）

以下は旧来の記述形式です。現行実装でも動きますが、**新規ジョブは §3（Sequence + scene_delta）を推奨**します。  
`constants`（%...%）/ `iterators`（$[...]）/ `fixed/random/parameter_combinations` は §3 と共通で、どちらの形式でも使えます。

### 8.1 Sequence の prompts 形式（フラット・旧）

`scene_delta` を使わず、プロンプトを1件ずつ**フラットに列挙**する形式です。差分継承がないため長いシリーズには不向きで、**`--scenes` による部分実行は使えません**（§3.10）。

```yaml
job_name: "sequence_demo"
job_type: "sequence"
base_workflow: "workflows/api_base.json"

prompt_target:
  node_id: 149
  input_name: "text"

prompts:
  - template: "1girl, <preset:quality#default>, __hair_color__"
    runs: 3
```

**リスト記法**（`List[str]` でも書ける。内部で `", "` 結合して template 化）:

```yaml
prompts:
  - ["%base_quality%", "1girl", "$[expression]", "$[location]"]
  - ["%base_quality%", "1boy", "serious"]
```

**runs の指定**（`default_runs` は §3.6 と同じ意味。ここでは各 prompt の `runs` が優先）:

```yaml
default_runs: 2
prompts:
  - template: "1girl, smile"            # 2回実行（default_runs）
  - template: "1boy, serious", runs: 5  # 5回実行（明示指定が優先）
```

### 8.2 GridSearch（job_type: grid_search）

複数軸の **全組み合わせ（デカルト積）** を実行します。

#### 8.2.1 最小例

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

#### 8.2.2 placeholders（プレースホルダー展開）

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

#### 8.2.3 処理順序・注意（現行実装）
- GridSearchでは、`variables` のうち **input_name に `text` を含む**ものだけを対象に、`{...}` を **事前展開**します（`core/executors/grid_search_executor.py`）。その後、各値（文字列）に対して `PromptResolverV2.resolve()` を実行します。
- 展開後に `itertools.product` で全組み合わせを作るため、`placeholders` が多いと実行数が爆発します。
