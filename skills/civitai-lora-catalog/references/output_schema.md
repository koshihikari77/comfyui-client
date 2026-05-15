# LoRA Catalog Output Schema

## Raw catalog

Path:

- `workspace/lora_catalog/civitai_loras.raw_versions.yaml`
- `workspace/lora_catalog/civitai_loras.raw_versions.jsonl`

Shape:

```yaml
catalog_version: 1
generated_at: "..."
source:
  type: civitai_collection
  collection_id: 15946059
  base_url: https://civitai.red
item_count: 43
items:
  - key: assistedpaizuriv2-000012
    name: Duo Paizuri Pack IL | Shrekman Hentai Loras
    model_id: 1328924
    model_version_id: 2624239
    version_name: AssistedPaizuriV2IL
    version_index: 4
    version_created_at: "..."
    version_published_at: "..."
    type: LORA
    base_model: Illustrious
    file_name: AssistedPaizuriV2-000012.safetensors
    file_id: 2483458
    hashes:
      SHA256: "..."
      AutoV2: "..."
    download_url: https://civitai.com/api/download/models/2624239
    page_url: https://civitai.com/models/1328924
    trigger_words:
      - "APV2, assisted paizuri, ..."
    description: "..."
    version_description: "..."
```

## Curated catalog

Path:

- `workspace/lora_catalog/civitai_loras.curated.yaml`
- `workspace/lora_catalog/civitai_loras.curated.jsonl`

Curated entries should keep the same fields as raw entries and add:

```yaml
curation:
  selected: true
  reason: distinct LoRA concept stored as a model version; keep latest/Illustrious variant
```

## Agent-facing fields

Most useful fields for prompt/job construction:

- `name`
- `version_name`
- `file_name`
- `model_id`
- `model_version_id`
- `base_model`
- `trigger_words`
- `description`
- `version_description`
- `agent_notes.aliases`
- `agent_notes.recommended_weight`
- `agent_notes.usage_notes`
