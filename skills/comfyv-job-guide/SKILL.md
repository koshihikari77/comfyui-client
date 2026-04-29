---
name: comfyv-job-guide
description: ComfyV の job YAML 記法ガイド。scene_delta、placeholder、constant、iterator、preset、wildcard の書き方と制約を確認したいときに使う。新しい job.yaml を書くときや既存 job の記法を理解したいときに参照。
---

# ComfyV 設定ファイル & プロンプト記法ガイド

job YAML の書き方、プロンプトテンプレートの記法、scene_delta の継承ルールを網羅したガイド。

## この Skill が向いている依頼

- 新しい job.yaml を書きたい
- scene_delta の `_from` 継承、`_add`/`_del`、`_unset`/`_invisible` の使い方を知りたい
- placeholder `{name}` / `{name:r}` / インライン `{a | b | c}` の違いを確認したい
- constant `%name%`、iterator `$[name]`、preset `<preset:...>` の記法を確認したい
- runs / default_runs の挙動を知りたい
- `--scenes` で部分実行する方法を知りたい

## ガイドソース

`/mnt/c/Users/inada/obsidian/base/03_projects/comfyui/documents/config_and_prompt_guide.md`

詳細はこのファイルを直接読むこと。

## クイックリファレンス

### ジョブ種別

| job_type | 動作 |
|----------|------|
| `grid_search` | 複数軸の全組み合わせ（デカルト積） |
| `sequence` | 定義されたプロンプトを上から順に実行 |

### プロンプト記法一覧

| 記法 | 意味 | 展開タイミング |
|------|------|---------------|
| `%name%` | Constant（定数置換） | Sequence前処理 |
| `$[name]` | Iterator（巡回置換） | Sequence前処理 |
| `<preset:name>` / `<preset:name#group>` | Preset（プリセット参照） | Resolve時 |
| `{name}` | Placeholder（直積展開） | Resolve時 |
| `{name:r}` | Placeholder（ランダム選択） | Resolve時 |
| `{a \| b \| c}` | インラインPlaceholder（直積） | Resolve時 |
| `{a \| b \| c:r}` | インラインPlaceholder（ランダム） | Resolve時 |
| `__name__` | Wildcard（ランダム1行） | Resolve時 |

### scene_delta 予約キー

| キー | 説明 |
|------|------|
| `_id` | シーンID（`_from` 参照用） |
| `_name` | 表示名 |
| `_from` | 継承元（ID or `base`） |
| `_runs` | このシーンの生成枚数 |
| `_unset` | slot の値を None にして出力除外 |
| `_invisible` / `_visible` | 値を維持して出力のみ制御 |
| `_add` | slot にタグ追加（累積） |
| `_del` | slot からタグ削除（完全一致） |
| `_params` | ワークフローパラメータ（set→以後継承） |

### slot の `+` / `-` 省略記法

```yaml
scene_delta:
  - { pose: "+hand up" }    # _add と同じ
  - { pose: "-standing" }   # _del と同じ
```

### パラメータ優先度

`scene_delta _params > parameter_combinations > random_parameters > fixed_parameters`

### 部分実行（--scenes）

```bash
uv run comfyv run job.yaml --scenes "0,2"           # index指定
uv run comfyv run job.yaml --scenes "scene_a"        # ID指定
uv run comfyv run job.yaml --scenes "3-7"            # 範囲
uv run comfyv run job.yaml --scenes "6-"             # 6から最後まで
```

## よくある参考 job

- `/mnt/c/Users/inada/obsidian/base/03_projects/comfyui/configs/jobs/base/` — 基本テンプレート
- `/mnt/c/Users/inada/obsidian/base/03_projects/pixiv/wakame/20260322_りりむ自慰バレ/job.yaml` — scene_delta + _from 継承の実践例（18シーン物語構成）
