---
name: comfyui-prompt-control-area-couple
description: comfyui-prompt-control の AREA / COUPLE 記法を使って、複数領域の prompt を組み立てたり、既存プロンプトの座標・タイミング指定を調整したいときに使う。
---

# comfyui Prompt Control Area Couple

## この Skill を使う場面

- `comfyui-prompt-control` の `AREA` / `COUPLE` 記法で prompt を書きたいとき
- 複数領域の prompt を step で切り替えたいとき
- 既存の AREA / COUPLE prompt を読んで修正したいとき

この skill は AREA / COUPLE の書き方に限定する。
scene_delta 全体の設計は別資料を読む。

---

## ⚠️ 最初に確認すること（外すと無音で壊れる）

**1. workflow のノード型**

| ノード | scheduling `[A:B:step]` | DEF |
|---|---|---|
| `PCTextEncode`（PC: Text Encode **(no scheduling)**） | **✗ 効かない** | ✗ |
| `PCLazyTextEncode`（PC: Schedule Prompt） | ○ | ○ |

`PCTextEncode` に `[AND AREA(...):COUPLE(...):0.3]` を書いても**スケジュールにならない**。
`AND` で split され、`[` `:0.3]` がゴミ token として残り、AREA と COUPLE が同時適用される。**エラーは出ない。**
→ スケジュール記法を使うなら **ノードを `PCLazyTextEncode` に差し替える**。

**2. fp8 では COUPLE がエラー** → fp16 にする。

**検証手順**: ノード型を確認 → `dump-prompts` で座標と展開を確認 → 生成。

---

## ★座標系は AREA と MASK/COUPLE で違う

```
AREA(x  width,  y  height)   ← 位置 と 大きさ
MASK/COUPLE(x1 x2, y1 y2)    ← 始点 と 終点
```

| | 左半分 | 右半分 |
|---|---|---|
| AREA | `AREA(0 0.5)` | `AREA(0.5 0.5)` |
| COUPLE | `COUPLE(0 0.5)` | **`COUPLE(0.5 1)`** |

AREA の数字をそのまま COUPLE に写すと `COUPLE(0.5 0.5)`＝**幅ゼロのマスク**になる（頻出バグ）。

---

## ★隙間（gap）は COUPLE と AREA で逆

| 使い方 | 隙間 |
|---|---|
| COUPLE / MASK 単体 | **空ける**（`COUPLE(0 0.45)` / `COUPLE(0.55 1)`） |
| AREA 単体（単純分割） | **密着**（隙間には base だけが強く出る） |
| AREA:COUPLE スケジュール | **密着でよい**。隙間を作るなら **`FILL()` が必要** |

---

## AREA と COUPLE の性質

| | 効き方 | 実装 | 速度 |
|---|---|---|---|
| **AREA** | 厳密。はみ出さない | 領域ごとに**別生成して合成** | 遅い |
| **MASK** | ヒント。はみ出す/融合する | 全体生成 → mask 適用 | 遅い |
| **COUPLE** | ヒント（attention） | **全解像度 1 パス** | 速い |

**「AREA だけだと淡い・未完成・コラージュ感」になるのは、領域ごとに別生成して合成しているから。**
定石 `[AND AREA(...):COUPLE(...):TIMING]` は **AREA 期を最小にして構図だけ固め、以降 COUPLE で馴染ませる**ためにある。

- `COUPLE AREA()` とは書けない（スケジュールで切り替える）。
- 0.1 以下の極小領域はほぼ描かれない。

---

## 横分割と縦分割 / split screen

- **横長の左右分割は打率が高い**（頭〜足が融合しない）。**純 COUPLE だけで十分**なことが多い。
- **縦（上下）分割は難しい** → `AREA:COUPLE` スケジュールが効く。
- **`split screen` / `comic` / `multiple views` は区切り線を生じさせるタグ**。縦分割の融合対策に使う。
  **一枚絵にしたいなら入れない**（入れなければ境目はぼける）。→ 横長の一体シーンでは使わない。

---

## TIMING

- 既定 **0.3**。総ステップ依存（30step なら 0.2 可、15step では早すぎ）。
- 大きいほど分離は強いが**遅く、別背景・別衣装が残りやすい**。失敗が続くなら 0.4〜0.6。`1.0` は全ステップ AREA。
- `1` より大きい整数は**絶対ステップ番号**（`[A:B:4]` = 4 ステップ目から B）。

---

## ベースプロンプト

- COUPLE/MASK 時、base は**全域に効き、領域へ滲む**（`FILL()` で限定）。AREA 時は薄くしか効かない。
- **base にキャラ固有タグ（髪色・目・服）を書かない**（混色の原因）。
- `2girls` は必須ではない。効かない時は削る / 強調の両方を試す。
- CFG を上げる・総ステップを増やすと反応が良くなる。

---

## 必要に応じて読む references

- `references/patterns.md` - 実用パターン（座標修正済み）
- `references/pitfalls.md` - 破綻しやすい点
- 詳細正本: `/mnt/c/Users/inada/obsidian/base/03_projects/comfyui/configs/prompts/prompt_control_area_couple.md`
- 実装: `prompt_control/prompts.py`（`get_area` / `make_mask` / `encode_prompt`）、`nodes_base.py`、`nodes_lazy.py`
