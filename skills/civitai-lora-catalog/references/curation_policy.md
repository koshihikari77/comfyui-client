# LoRA Curation Policy

## 入力

raw catalog:

- `workspace/lora_catalog/civitai_loras.raw_versions.yaml`
- `workspace/lora_catalog/civitai_loras.raw_versions.jsonl`

raw は collection 内の model を全 version 展開したもの。これは判断前の一次データとして残す。

## 抽出ルール

### 1. 同一 LoRA の version 違い

最新版を残す。

判断材料:

- `version_name`
- `version_created_at`
- `version_published_at`
- `file_name`
- `trigger_words`
- description 内の changelog

例:

- `v0.42 Illustrious` と `v1.0-LR Illustrious` が同じ用途なら `v1.0-LR` を残す。

### 2. version ごとに別 LoRA が入っている model

各種類を残す。

判断材料:

- version名が別コンセプト名になっている
- file名の stem が別物
- trigger prefix が別物

例:

- `Duo Paizuri Pack` の `AssistedPaizuriV2IL`, `CooperativePaizuriV2`, `ButtJob-X-PaizuriV1` は別 LoRA として残す。

### 3. base model 違い

Illustrious 系を優先する。

優先順:

1. `Illustrious`
2. `NoobAI` / Noob-Illustrious 系。ただし Illustrious 版があれば Illustrious 版を優先。
3. `Pony`
4. `SDXL 1.0`
5. `SD 1.5`

同じ LoRA の base model variant が複数ある場合、Pony / SDXL / SD 1.5 は原則落とす。

### 4. collection内の重複 model

別 model に旧版、pack model に新版がある場合は新版を優先する。

例:

- standalone `Cooperative Paizuri` と pack 内 `CooperativePaizuriV2` があるなら、pack 内 V2 を残す。
- standalone `Fellatio Through Another's Paizuri` と pack 内 `FellatioThroughAnother'sV2` があるなら、pack 内 V2 を残す。

## notes に残すこと

`workspace/lora_catalog/civitai_loras.curation_notes.md` に以下を書く。

- raw / curated / dropped 件数
- selected の version id, name, version, base model, file name
- dropped の version id, name, version, base model, file name, drop reason

