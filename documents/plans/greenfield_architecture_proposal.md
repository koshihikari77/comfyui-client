# ComfyV 新規設計提案

## 目的

この文書は、現行実装の構造を前提にしつつも、**もし ComfyV を最初から作り直すならどう設計するか**を整理した提案です。  
コード変更方針ではなく、まず「このプロジェクトで本当にやりたいことは何か」を明文化し、そのうえでゼロベースの形を定義します。

---

## 1. このプロジェクトでやりたいこと

ComfyV が本質的にやりたいことは、単なる ComfyUI の API クライアントではありません。

### 1.1 中核の価値

1. **画像生成実験を宣言的に書けること**
   - YAML とプロンプト記法で、試したい条件をコードなしで定義できる
2. **大量の組み合わせ実験を安全に回せること**
   - grid_search と sequence を使い分け、実験意図に応じた実行ができる
3. **プロンプトの表現力を高く保つこと**
   - preset, wildcard, placeholder, constant, iterator, scene_delta などを組み合わせて短く書ける
4. **結果の再現性を残すこと**
   - 実行時の workflow, prompt, parameters, 生成物を後から追える
5. **実験を比較・評価しやすくすること**
   - 実行後に「何を変えてどう出力が変わったか」を辿れる

### 1.2 ユーザーがやりたい作業

- LoRA や sampler や CFG の比較
- 同じテーマで prompt だけを変えて連続生成
- scene_delta で差分管理しながらシーンを量産
- preset と wildcard を使って prompt の記述量を減らす
- 実行前に dump-prompts で展開結果を確認
- 実行後に画像と使用条件をまとめて見返す

### 1.3 非機能要件

- **再現性**: 実行後に再現できる
- **説明可能性**: なぜその prompt / parameter になったか追える
- **拡張性**: 新しい記法や実行方式を足しやすい
- **テスト容易性**: ComfyUI 本体なしでも大半を検証できる
- **失敗耐性**: 実行途中失敗でもどこまで進んだか残る

### 1.4 逆に中核ではないもの

- PromptResolver V1 互換の維持
- DI コンテナ自体の存在
- SQLite という実装選択そのもの
- 現在の `core/` 配下の分け方

---

## 2. ゼロから作るならの基本方針

結論として、**設定ファイルを直接実行するアプリ**ではなく、**設定をコンパイルして実験計画に落とし、その計画を実行するアプリ**として作るべきです。

つまり中心概念は `Config` ではなく、次の 3 つです。

1. `JobSpec`
   - ユーザーが書く宣言的入力
2. `ExecutionPlan`
   - 実行前にコンパイルされた計画
3. `RunResult`
   - 1 回の実行の完全な結果

この 3 層に切ると、記法追加・実行方式追加・レポート改善が全部やりやすくなります。

---

## 3. 提案アーキテクチャ

### 3.1 レイヤ構成

```text
CLI / API
  -> Application UseCases
    -> Domain Services
      -> Infrastructure Adapters
```

### 3.2 役割

#### Interfaces

- CLI
- 将来必要なら Python API

#### Application

- `run_job`
- `dump_prompts`
- `eval_prompt`
- `resume_job`
- `report_job`

ここはユースケースの流れだけを持ち、記法の詳細や DB 実装は持たない。

#### Domain

- JobSpec の検証
- scene_delta のコンパイル
- prompt template の解決
- run planning
- workflow parameter binding
- run result の組み立て

ここがプロジェクトの中心。

#### Infrastructure

- ComfyUI API adapter
- Repository 実装
- SQLite / file storage
- HTML report renderer

---

## 4. 中心データモデル

### 4.1 JobSpec

ユーザーの YAML をそのまま表す入力モデル。

- job_name
- job_type
- workflow_ref
- prompt_source
- variables
- fixed/random/combination parameters
- constants
- iterators
- placeholders
- scene_delta
- output policy

### 4.2 CompiledJob

JobSpec を正規化した中間表現。

- prompt target
- normalized scenes/prompts
- normalized parameter sources
- resolver settings
- artifact policy

### 4.3 ExecutionPlan

実際に何回回るのかを明示した計画。

- job metadata
- total run count
- run list or run iterator
- dependencies
- report metadata

### 4.4 RunSpec

1 回の実行単位。

- run_id
- scene_id
- resolved prompt
- resolved parameters
- bound workflow
- seed / random context
- provenance
  - どの constant / iterator / placeholder / preset から来たか

### 4.5 RunResult

- run_id
- status
- prompt_id
- output files
- final workflow
- final parameters
- logs / errors
- timestamps

---

## 5. 主要コンポーネント

### 5.1 Job Loader

責務:

- YAML 読み込み
- パス解決
- schema validation

ここでは scene_delta 展開や prompt 解決はしない。入力を安全に受けるところで止める。

### 5.2 Job Compiler

責務:

- `scene_delta -> normalized prompt scenes`
- constants / iterators / placeholders の解決準備
- grid_search / sequence の共通中間表現化

このコンポーネントを中核に置くべきです。  
現行実装ではここに相当する責務が `config.py`, `cli.py`, `sequence_executor.py`, `grid_search_executor.py` に散っています。

### 5.3 Prompt Engine

責務:

- preset
- placeholder
- wildcard
- filter
- format

これは現行の PromptResolver V2 の発想を継承してよいです。  
ただし「単に文字列を返す」だけでなく、**展開根拠も返せる設計**にするのが理想です。

返り値イメージ:

```text
ResolvedPrompt {
  text: "...",
  used_presets: [...],
  used_placeholders: [...],
  used_wildcards: [...],
}
```

### 5.4 Planner

責務:

- grid_search の直積計画作成
- sequence の逐次計画作成
- run 数の確定
- dry-run / dump 用の共通出力

`dump-prompts` も `run` も同じ plan を使うべきです。  
違いは「実行するか」「出力するか」だけにします。

### 5.5 Workflow Binder

責務:

- `node.input -> value` を workflow に適用
- ノード名参照の解決
- workflow の妥当性チェック

### 5.6 Run Executor

責務:

- 1 run 実行
- API 呼び出し
- 完了待ち
- 画像取得
- 結果の永続化

ここは prompt や planning を知らない方がよいです。  
受け取った `RunSpec` を処理するだけにします。

### 5.7 Repositories

- `JobRepository`
- `RunRepository`
- `ArtifactRepository`

少なくとも `job` と `run` は分けるべきです。  
現行の `images` 中心では、再実行や失敗追跡や report 再生成の単位が弱いです。

### 5.8 Reporter

責務:

- `RunResult` の集合を view model 化
- HTML などにレンダリング

workflow JSON を後から逆解析するのではなく、最初から `RunResult` ベースで組み立てるべきです。

---

## 6. ディレクトリ構成案

```text
comfyv/
├── app/
│   ├── cli/
│   │   └── main.py
│   ├── usecases/
│   │   ├── run_job.py
│   │   ├── dump_prompts.py
│   │   ├── eval_prompt.py
│   │   └── report_job.py
│   └── dto/
├── domain/
│   ├── job/
│   │   ├── models.py
│   │   ├── loader.py
│   │   ├── compiler.py
│   │   └── planner.py
│   ├── prompt/
│   │   ├── models.py
│   │   ├── engine.py
│   │   ├── parser.py
│   │   ├── preset.py
│   │   ├── placeholder.py
│   │   ├── wildcard.py
│   │   ├── filter.py
│   │   └── formatter.py
│   ├── workflow/
│   │   ├── loader.py
│   │   ├── binder.py
│   │   └── references.py
│   ├── run/
│   │   ├── models.py
│   │   ├── executor.py
│   │   └── policies.py
│   └── reporting/
│       └── assembler.py
├── infra/
│   ├── comfyui/
│   │   └── client.py
│   ├── persistence/
│   │   ├── sqlite/
│   │   │   ├── jobs.py
│   │   │   ├── runs.py
│   │   │   └── artifacts.py
│   │   └── files.py
│   └── reporting/
│       └── html_renderer.py
├── schemas/
│   └── job_config.py
├── templates/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── documents/
```

`core/` に全部置くより、責務で分けた方が新規参加者にも追いやすいです。

---

## 7. 実行フロー案

### 7.1 run

1. JobSpec を読む
2. validate する
3. CompiledJob にする
4. ExecutionPlan を作る
5. 各 RunSpec を順に実行する
6. RunResult を保存する
7. job 全体の report を生成する

### 7.2 dump-prompts

1. JobSpec を読む
2. CompiledJob にする
3. ExecutionPlan を作る
4. RunSpec から prompt 部分だけ出力する

### 7.3 eval-prompt

1. Prompt Engine に単発入力する
2. resolved text と provenance を返す

---

## 8. 仕様として先に固定したいこと

ゼロから作るなら、次は早い段階で固定したいです。

### 8.1 Sequence と GridSearch の共通化

- 両者とも最終的には `RunSpec` を作るだけ
- 違いは「RunSpec の作り方」だけ

### 8.2 prompt 解決と parameter 解決の分離

- prompt の DSL 展開
- workflow parameter の適用

この 2 つは混ぜない方が保守しやすいです。

### 8.3 実行前に run 数が分かること

- dry-run
- cost estimation
- 実行確認

このためにも planner は独立必須です。

### 8.4 provenance を残すこと

「最終 prompt」だけだと後で弱いです。  
少なくとも次は残したいです。

- 元 template
- 展開後 prompt
- 使用した preset group
- placeholder の選択結果
- iterator の選択結果
- 最終 parameters
- workflow snapshot

---

## 9. 最初のリリースで入れる範囲

全部を一気に作らず、最初の完成ラインは次で十分です。

### v0 の必須

- sequence
- grid_search
- prompt resolver v2 相当
- workflow binding
- run persistence
- dump-prompts
- HTML report

### v0 では後回しでよい

- legacy compatibility
- 複数 report format
- 並列実行
- job resume
- GUI

---

## 10. 提案の要点

このプロジェクトをゼロから作るなら、次の一文に尽きます。

**ComfyUI を叩くツールとしてではなく、画像生成実験を宣言・展開・実行・記録するための実験基盤として設計する。**

そのための核は以下です。

- `JobSpec` を受ける
- `ExecutionPlan` にコンパイルする
- `RunSpec` を実行する
- `RunResult` を永続化する

この形にすると、scene_delta も prompt 記法も executor も report も、全部が同じ軸で整理できます。
