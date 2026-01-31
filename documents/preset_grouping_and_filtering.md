# Preset グループ化 & フィルタリング拡張

ComfyV v2.1 で導入予定の **Preset 拡張仕様** と、関連するコード変更点をまとめます。

---
## 1. 目的
1. Preset 内でタグ集合に名前を付け、ユースケースに応じて使い分けたい。
2. "このタグ／グループは今回のジョブでは除外したい" といったフィルタリングを容易にしたい。
3. YAML を横書きでも記述出来るようにし、可読性を向上させたい。

---
## 2. 新しい Preset YAML フォーマット

```yaml
# prompts/presets/quality.yaml
# ルートが dict の場合、キーをグループ名として解釈
# 値は list でも 1 行カンマ区切り文字列でも OK

default:
  - masterpiece, best quality, finely detailed  # 横書き
low:
  - high quality
hdr:
  - HDR
```

* 既存の **リスト形式のみ** のファイルは暗黙に `default` グループへ格納され後方互換。
* ネスト構造もそのまま： `characters/hero.yaml` 内で `base:` などのグループ定義が可能。

---
## 3. 呼び出しシンタックス

| 例 | 説明 |
| --- | --- |
| `<preset:quality>` | `quality#default` と同義 |
| `<preset:quality#low>` | `low` グループのみ呼び出し |
| `<preset:quality#default+hdr>` | `default ∪ hdr` を結合 |
| `<preset:quality#default-hdr>` | `default − hdr` (除外) |

**※注意** 異なる Preset をまたいだ演算 (`<preset:quality+style#anime>` など) は現行仕様では未定義です。サポート外のため将来の互換性は保証されません。

構文: `<preset:キー#式>` で `式` は `group1 (+ group2 …) (- groupX …)` を組み合わせ可。

---
## 4. フィルタリング機能 (JobConfig)

```yaml
ignore_tags:    # 個別タグ単位
  - HDR
  - lowres
ignore_groups:  # preset#group 単位
  - quality#low
```
`PromptResolver` が最終生成文字列から除外します。

---
## 5. 横書きサポート

Preset YAML の値（リスト要素）が **文字列 1 行** の場合、
カンマ `,` または 全角読点 `、` で分割して複数タグとして扱います。

---
## 6. 実装変更点

### 6.1 PromptResolver (`core/prompt_resolver.py`)
1. `__init__` に `config: Config | None = None` を追加し、`ignore_tags` 等を参照可能に。
2. `_load_definitions()`
   * YAML が `list` → `{'default': list}` へ変換。
   * 値が `str` の場合 `re.split('[,、]', item)` でタグ分割。
3. `_get_preset_values(key_expr)` を新規実装。
4. `_resolve_presets()` 内で上記パーサを使用。
5. `resolve()` の末尾で `ignore_tags` / `ignore_groups` を適用。

### 6.2 Config (`core/config.py`)
* `ignore_tags` / `ignore_groups` キーを許可し、型チェックを追加。
* プロパティ `ignore_tags`, `ignore_groups` を追加。

### 6.3 ServiceContainer (`core/service_container.py`)
* `PromptResolver` 生成時に `self.config` を渡すよう修正。

### 6.4 UnitTest 追加
* グループ選択・除外、横書き、フィルタリングを検証するテストケースを `tests/test_prompt_resolver.py` に追記。

---
## 7. 後方互換性
1. **旧 YAML**（リストのみ）は自動で `default` に取り込まれる。
2. **旧シンタックス** `<preset:key>` はそのまま動作。
3. 既存テストは維持されるが、新機能用テストを追加推奨。

---
## 8. 移行手順
1. グループ化したい YAML だけを dict 構造へ書き換え。
2. JobConfig で必要に応じ `ignore_tags` / `ignore_groups` を記述。
3. ServiceContainer, PromptResolver, Config を上記変更に合わせて更新。
4. テストを実行し動作確認。

---
## 9. 将来拡張案
* Preset グループ間での **重み付け** (タグに優先度を付与)。
* `ignore_` ではなく `include_only:` を追加し、ホワイトリスト運用も可能に。
* GUI で Preset/Group をプレビュー・選択できるビルダーの提供。

---
以上。

