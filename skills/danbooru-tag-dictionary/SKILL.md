---
name: danbooru-tag-dictionary
description: シーン構築用のdanbooruタグ辞書。体位・表情・手足・射精・エフェクト・構図などのタグをカテゴリ別に引きたいときに使う。job.yamlのscene_deltaやplaceholderで使うタグの正しい書き方を確認できる。
---

# Danbooru タグ辞書（シーン構築用）

シーンのプロンプトを組み立てるとき、正しいdanbooruタグを参照するための辞書。

## この Skill が向いている依頼

- job.yaml の scene_delta でシーンを書くとき、正しいタグ名を確認したい
- 表情・体位・手の動作・エフェクトなどのタグ候補を一覧したい
- pose_combinations（体位の組み合わせ例）を参考にしたい
- 「このシチュエーションにはどんなタグがあるか」を探したい

## 辞書ソース

`/mnt/c/Users/inada/obsidian/base/03_projects/comfyui/configs/prompts/danbooru-tag-scenes-organized.yaml`

タグを探すときはこのファイルを直接読むこと。

## 辞書の構造

### common_parts（体位に依存しない共通パーツ）

| カテゴリ | サブカテゴリ | 内容 |
|----------|-------------|------|
| `male_hand` | grab / hold / head | 男性の手・腕の動作 |
| `female_hand` | self_touch / grab / position / partner | 女性の手・腕の動作 |
| `female_leg` | spread / raised / other | 女性の脚の状態 |
| `expression` | basic / pleasure / eyes / mouth / other | 表情パーツ（単体タグ） |
| `expression_sets` | — | 表情セット（組み合わせ済みテンプレート） |
| `looking` | — | 視線（looking at viewer, looking away, etc.） |
| `facing` | — | 顔の向き（facing forward, face down, etc.） |
| `cum` | oral / body / internal / action | 射精・汚れ |
| `effects` | motion / visual / body | エフェクト |
| `shot` | angle / focus / framing | カメラアングル・構図 |
| `body` | breasts / lower / other | 体の状態 |
| `clothing_status` | open / lift / pull / nude | 服の状態 |
| `pose` | lying / standing / sitting / bent / presenting / specific | 体全体の姿勢 |
| `pose_combinations` | base / specific | 体位の組み合わせ例 |
| `action` | position / fellatio / licking / paizuri / hand / motion / before | 性行為の動作 |
| `position_modifiers` | missionary / sex_from_behind / cowgirl / fellatio / paizuri / standing_sex | 体位固有の修飾タグ |

### split（特殊シーン）

- `2koma`, `split screen`

## 使い方

1. まず辞書ソースを読んで該当カテゴリのタグ一覧を確認
2. タグの存在が不確かなら `tagdb check "tag1, tag2"` で検証
3. 実際の使用例を見たいなら `tagdb posts "tag1, tag2" --top-k 5` で確認

## 注意

- このファイルはdanbooruの実在タグを収集したものだが、網羅的ではない
- 新しいタグや確信のないタグは必ず `tagdb check` / `tagdb fuzzy` で検証すること
- expression_sets と pose_combinations は `{a | b}` インライン記法を含む（ComfyVのplaceholder展開用）
