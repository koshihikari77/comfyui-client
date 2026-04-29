---
name: comfyui-overview
description: ComfyUI workflow を job YAML で回し、prompt 解決、grid search、sequence 実行、結果保存まで扱いたいときに使う。ComfyV CLI の入口と重要ファイルもこの skill から辿れる。
---

# comfyui Overview

## この Repo でできること

- ComfyUI API を使った画像生成ジョブを実行できる
- job YAML、workflow JSON、prompt preset を組み合わせて batch 実行できる
- grid search、sequence 実行、結果保存を一つの CLI で扱える

## この Skill が向いている依頼

- ComfyUI workflow を手で叩く代わりに job 単位で安定実行したい
- prompt preset と workflow を分離して管理したい
- この repo の入口や主要ファイルを確認したい場合は `references/` を読む

## この Repo の責務

- ComfyUI API を使った画像生成ジョブ実行フレームワークを提供する
- job YAML、workflow JSON、prompt 解決、実行結果保存を管理する
- Grid Search と Sequence 実行を提供する

## この Repo が責務として持たないもの

- ComfyUI server 自体の運用
- 生成後の後処理、吹き出し合成、投稿戦略

## 主要成果物

- `/mnt/c/Users/inada/obsidian/base/03_projects/comfyui/configs/jobs/` - job 定義
- `/mnt/c/Users/inada/obsidian/base/03_projects/comfyui/configs/workflows/` - ComfyUI workflow JSON
- `/mnt/c/Users/inada/obsidian/base/03_projects/comfyui/configs/prompts/` - preset / wildcard / tag 設定
- `/mnt/c/Users/inada/obsidian/base/03_projects/comfyui/results/` - 実行結果と SQLite

## 典型的なワークフロー

1. 接続先と prompt 設定を確認する
2. job YAML を用意する
3. `comfyv run` で job を実行する
4. `results/` と SQLite を確認する

## 受け渡し点

- 入力: job YAML、workflow JSON、prompt preset
- 出力: 生成画像、実行結果、SQLite 記録

## 必要に応じて読む references

- `references/key-files.md` - 初見で重要ファイルと読む順番を確認したいとき
- `references/commands.md` - 実行コマンドを確認したいとき
- `references/pitfalls.md` - path や設定で詰まったとき
