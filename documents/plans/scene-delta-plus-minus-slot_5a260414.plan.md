---
name: scene-delta-plus-minus-slot
overview: "scene_delta の通常 slot で、値が \"+...\" のときは _add、\"-...\" のときは _del と同様に扱う記法を追加する。`pose: +\"hand up\"` や `pose: -\"standing\"` のように書けるようにする。"
todos: []
isProject: false
---

# scene_delta で slot に + / - 記法を追加する

## ゴール

- **通常の slot 指定**で、値の先頭が `+` なら「その slot に追加」、`-` なら「その slot から削除」とする。
- 既存の `_add` / `_del` はそのまま残し、同じシーン内で混在可能（例: `pose: +"hand up"` と `_add: { extra: "tag" }`）。
- YAML では `pose: '+"hand up"'` や `pose: "-standing"` のように文字列で指定する想定。

## 仕様


| 記法                                       | 意味                | 既存との対応                        |
| ---------------------------------------- | ----------------- | ----------------------------- |
| `slot: "value"` または `slot: [a, b]`       | 上書き（set）          | 現状どおり                         |
| `slot: +"value"` / `slot: "+tag1, tag2"` | その slot に追加       | `_add: { slot: "value" }` と同じ |
| `slot: -"value"` / `slot: "-tag1, tag2"` | その slot から完全一致で削除 | `_del: { slot: "value" }` と同じ |


- 値は **文字列** の場合のみ `+` / `-` を解釈する。先頭の空白 trim 後、`+` または `-` で始まる場合に追加/削除扱いとする。
- 追加/削除するタグは、`+` または `-` の**直後以降**の文字列を `_normalize_slot_value` と同様に正規化（カンマ区切り分割・constants 展開）してリスト化する。
- **リスト**値（例: `pose: ['+hand up', '-standing']`）は、要素ごとに先頭が `+`/`-` なら追加/削除を順に適用する形で対応すると、1 slot で「追加と削除を両方」書ける。未対応でもよい場合は、まずはスカラ文字列のみ対応とする。

## 実装方針

処理は [core/config.py](core/config.py) の `_compile_delta_items` 内で行う。現在の流れは次のとおり。

1. `_from` で current_state / current_visibility を決定
2. **予約キー以外の key** について `current_state[key] = _normalize_slot_value(value)` で set
3. `_unset` 適用
4. `_add` 適用
5. `_del` 適用

変更案:

- 手順 2 の「set」のループで、`value` が**文字列**かつ `value.strip().startswith('+')` または `value.strip().startswith('-')` のときは、**set ではなく**「追加用」「削除用」の一時 dict に slot 名と正規化したタグリストを入れる。
- ループ後に、その一時 dict を使って現在の `_add` / `_del` と**同じロジック**で current_state を更新する（既存の `_add` / `_del` ブロックの**前**に、この「slot 由来の add/del」を実行するか、あるいは set ループの直後に「slot +/- の add/del」を実行する）。

つまり、「set のループ」を次のように分ける。

1. 予約キー以外を走査:
  - 値が str で `strip()` 後 `+` 始まり → `add_from_slot[key] = _normalize_slot_value(value[1:].strip(), constants)` を登録（key が複数回でた場合は上書きでよい）。
  - 値が str で `strip()` 後 `-` 始まり → `del_from_slot[key] = _normalize_slot_value(value[1:].strip(), constants)` を登録。
  - それ以外 → 従来どおり `current_state[key] = _normalize_slot_value(value, constants)`。
2. 続けて、`add_from_slot` を現在の `_add` と同じロジックで current_state に反映。
3. `del_from_slot` を現在の `_del` と同じロジックで current_state に反映。
4. その後、既存の `_unset` → `_add` → `_del` の順はそのまま。

これで `pose: +"hand up"` は「pose に "hand up" を追加」、`pose: -"standing"` は「pose から "standing" を削除」になる。

## 変更ファイル

- **[core/config.py](core/config.py)**  
  - `_compile_delta_items` 内の「予約キー以外の key で set」のループを上記のように変更。  
  - 必要なら `_parse_slot_add_del_value(value, constants) -> Optional[Tuple[Literal['add','del'], List[str]]]` のような補助関数を追加し、`+`/`-` 判定と正規化をまとめてもよい。
- **[documents/config_and_prompt_guide.md](documents/config_and_prompt_guide.md)**  
  - 7.2 または 7.4 付近に、「slot に `+` / `-` を付けた値で追加・削除できる」旨と、`pose: +"hand up"` / `pose: -"standing"` の例を追記。
- **テスト**  
  - [tests/test_config.py](tests/test_config.py) の scene_delta 系で、`pose: '+"hand up"'` で追加されること、`pose: '-"standing"'` で削除されること、および既存の `_add`/`_del` と混在した場合の順序が期待どおりであることを検証するケースを追加。

## リスト値（オプション）

`slot: ['+a', '-b']` のようにリストで複数の +/- を指定する場合は、先頭から順に「追加」「削除」を適用するようにすると、1 行で追加と削除を両方書ける。スコープを小さくするなら、まずは**スカラ文字列のみ**（`slot: +"hand up"` / `slot: -"standing"`）対応とし、リストは後追いでもよい。

## 注意（YAML）

- 値が `+` や `-` で始まる場合、YAML では数値と解釈されないよう **クォート** する必要がある（例: `pose: '+"hand up"'`、`pose: "-standing"`）。ドキュメントにその旨を書く。

---

## 実装結果（完了）

- **core/config.py**: `_compile_delta_items` 内で、予約キー以外の key を走査するループを変更。値が str かつ先頭が `+` / `-` のときは `add_from_slot` / `del_from_slot` に正規化タグを登録し、それ以外は従来どおり set。ループ直後に add_from_slot / del_from_slot を _add / _del と同じロジックで current_state に反映。補助関数は未追加（ループ内で直接判定）。
- **documents/config_and_prompt_guide.md**: 7.4 付近に「slot の `+` / `-` 記法」を追記。記法は **`pose: "+hand up"`** / **`pose: "-standing"`** とし、外側クォート不要でよい旨を記載。
- **tests/test_config.py**: `test_scene_delta_slot_plus_minus_notation`（`+hand up` で追加、`-standing` で削除）、`test_scene_delta_slot_plus_minus_mixed_with_add_del`（同一シーンで slot `+` と `_add` 混在）を追加。
- リスト値（`slot: ['+a', '-b']`）は未対応。スカラ文字列のみ対応。

