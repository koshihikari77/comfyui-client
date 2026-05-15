---
name: civitai-lora-catalog
description: Civitai/Civitai Red の collection から LoRA カタログを作る。collection内モデルの全versionをraw化し、同一LoRAは最新版、別LoRAは維持、base model違いはIllustrious系優先でagent向けcurated YAML/JSONLを作るときに使う。
---

# Civitai LoRA Catalog

## 目的

Civitai / Civitai Red の collection を、agent が読める LoRA カタログへ変換する。

この skill では `scripts/civitai_lora_catalog.py` を使う。token や生成カタログは repo に入れず、`workspace/lora_catalog/` に置く。

## 基本手順

1. `CIVITAI_API_TOKEN` が設定されているか確認する。値は表示しない。
   ```bash
   test -n "$CIVITAI_API_TOKEN" && echo set || echo unset
   ```

2. collection の全 modelVersion を raw 化する。
   ```bash
   uv run python skills/civitai-lora-catalog/scripts/civitai_lora_catalog.py \
     --collection "https://civitai.red/collections/<collection_id>" \
     --all-versions
   ```

3. raw を読む。
   - `workspace/lora_catalog/civitai_loras.raw_versions.yaml`
   - `workspace/lora_catalog/civitai_loras.raw_versions.jsonl`

4. curated を作る。
   - 同一 LoRA の version 違いは最新版を残す。
   - version ごとに別 LoRA が入っている model は、各種類を残す。
   - base model 違いは Illustrious / NoobAI-Illustrious 系を優先し、Pony / SD 1.5 / SDXL 1.0 だけの旧variantは原則落とす。
   - 判断理由を `workspace/lora_catalog/civitai_loras.curation_notes.md` に残す。

## 重要な注意

- `https://civitai.red/...` の collection は `civitai.com` API では item が空になることがある。collection URL の host を維持して取得する。
- collection API は private collection だと token が必要。token は環境変数で扱い、チャットやファイルに書かない。
- raw は削らない。curated は判断済みの agent 用ビューとして作る。
- 実ファイル名は `file_name`、Civitai ID は `model_id` / `model_version_id`、trigger は `trigger_words` を見る。

## 参照

- 詳しい抽出方針: `references/curation_policy.md`
- 出力 schema: `references/output_schema.md`
