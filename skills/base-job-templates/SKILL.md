---
name: base-job-templates
description: 体位別の job.yaml テンプレート集。騎乗位・フェラ・正常位・バック・立位の Normal/Abnormal テンプレートを参照し、新しい job を書くときの雛形にする。シーン構成（setup→during→climax→after）やplaceholder設計パターンも確認できる。
---

# 体位別 job.yaml テンプレート集

キャラを差し替えて体位別シーンを生成するためのベーステンプレート。
新しい job.yaml を書くときの雛形として使う。

## この Skill が向いている依頼

- 新しい体位の job.yaml を書きたい（雛形が欲しい）
- scene_delta のシーン構成パターン（setup→during→climax→after）を参考にしたい
- placeholder の設計パターン（表情プール、ポーズプール等）を見たい
- `_add` / `_del` / `_from` の実践的な使い方を確認したい
- Normal（通常）と Abnormal（荒っぽい）の味付けの違いを確認したい

## テンプレート一覧

ソースディレクトリ: `/mnt/c/Users/inada/obsidian/base/03_projects/comfyui/configs/jobs/base/`

| ファイル | 体位 | 味 | シーン数 | 概要 |
|----------|------|-----|---------|------|
| `cowgirl_position_normal.yaml` | 騎乗位 | Normal | 8 | 跨る→基本→腰振り→反り返り→前傾→中出し→事後 |
| `fellatio_normal.yaml` | フェラ | Normal | 13 | ベース→キス→手コキ→竿舐め→玉舐め→咥える→ディープ→抱きつき→射精→口内見せ→ごっくん |
| `fellatio_abnormal.yaml` | フェラ | Abnormal | 18 | イラマチオ・荒っぽいフェラ、掴み・押し込み系 |
| `missionary_normal_.yaml` | 正常位(全体位網羅) | Normal | 13 | 見せつけ→基本→プレス→指絡め→各中出し→事後 |
| `missionary_abnormal.yaml` | 正常位 | Abnormal | 8 | 押さえつけ、プレス、首絞め等 |
| `sex_from_behind_normal.yaml` | バック | Normal | 8 | 四つん這い→寝バック→座位→中出し→事後 |
| `sex_from_behind_abnormal.yaml` | バック | Abnormal | 9 | 押さえつけ・ピン留め・激しいバック |
| `standing_sex_normal.yaml` | 立位 | Normal | 11 | 抱き上げ→片足上げ→壁→密着→後ろから→前かがみ→事後 |

## 共通設計パターン

### シーン構成（4フェーズ）

```
setup  → 導入（見せつけ、跨る等）
during → 行為中（バリエーション複数）
climax → 射精（中出し、口内射精等）
after  → 事後（満足顔、見せつけ等）
```

### 命名規則

`{体位}_{味}_{フェーズ}_{バリアント}`
- 体位: `miss`, `behind`, `cowg`, `stand`, `oral`, `paiz`, `hj`
- 味: `n`(normal), `r`(rough/abnormal)
- フェーズ: `setup`, `during`, `climax`, `after`

### placeholder カテゴリ（Normal味の共通パターン）

| placeholder名 | 用途 |
|---------------|------|
| `n_male_hand` | 男性の手の動作 |
| `n_female_hand` | 女性の手の動作 |
| `n_female_leg` | 女性の脚の状態 |
| `n_expression` | 行為中の表情 |
| `n_intense_expression` | 激しめの表情 |
| `n_climax_expression` | 射精時の表情 |
| `n_after_expression` | 事後の表情 |
| `n_shot` | カメラアングル |
| `n_looking` | 視線 |
| `n_effect` | エフェクト |

### キャラ差し替え用 constant

全テンプレート共通で以下の constant が空配列で用意されている:
```yaml
constants:
  base_style: []      # ← 画風LoRA等
  char_base: []       # ← キャラタグ
  char_hair: []       # ← 髪タグ
  char_eyes: []       # ← 目タグ
  char_body: ["large breasts"]  # ← 体型
```

### prompt_template slot 構成（共通）

```
people → character → BREAK → style → BREAK → hair, eyes → BREAK →
body → BREAK → action, pose, pose_mod → BREAK →
male_hand, female_hand, female_leg → BREAK →
expression, looking → BREAK → shot, effect → BREAK →
background → BREAK → extra → BREAK → quality_tags
```

### 実践パターン

- **`_add` でタグ累積**: `_add: { extra: ["vaginal"] }` → 以後のシーンに継承
- **`_del` でタグ除去**: `_del: { effect: ["motion lines"] }` → 事後シーンで動きを消す
- **`_from: "base"` でリセット**: 事後シーンでテンプレート初期状態に戻す
- **`_params` でワークフロー制御**: LoRA重みをシーン途中で変更
- **インライン `{a | b:r}`**: 1箇所だけの使い捨て選択肢
