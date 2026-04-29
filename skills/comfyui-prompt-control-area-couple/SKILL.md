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

## まず読む順番

1. `/mnt/c/Users/inada/obsidian/base/03_projects/comfyui/configs/prompts/prompt_control_area_couple.md`
2. `references/patterns.md`
3. `/mnt/c/Users/inada/obsidian/base/03_projects/comfyui/configs/prompts/シーンプロンプトのつくり方.md`
4. `/mnt/c/Users/inada/obsidian/base/03_projects/comfyui/configs/prompts/danbooru-tag-scenes-organized.yaml`

## この Skill の責務

- `DEF`, `[A:B:step]`, `AREA`, `COUPLE` の意味を素早く思い出せるようにする
- 座標の切り方と TIMING の使い方を整理する
- 「序盤 AREA、後半 COUPLE」で固めてから馴染ませる定石を再利用できるようにする

## まず押さえるべきルール

- `DEF(NAME=value)` でマクロ化する
- `[A:B:step]` は `step` まで A、その後 B
- `AREA(x1 width, y1 height)` は矩形を強く分ける
- `COUPLE(...)` は同じ矩形をブレンド寄りに扱う
- 定石は `AREA(...):COUPLE(...):TIMING`
- 座標は 0〜1 の正規化値で、隙間なく並べる

## 典型的なワークフロー

1. ベース prompt と共通マクロを `DEF` で切る
2. 領域を 0〜1 座標で分割する
3. 各領域に AREA ブロックを書く
4. 同じ領域に COUPLE フェーズを重ねる
5. 必要ならタグや人数タグも step で切り替える

## ハマりどころ

- 座標に隙間があると、その部分にベース prompt だけが出やすい
- `AREA` だけで終えると境界が不自然になりやすい
- `TIMING` や人数タグの切り替えを雑にすると破綻しやすい

## 必要に応じて読む references

- `references/patterns.md` - 実用パターンの要約
- `references/pitfalls.md` - 破綻しやすい点
