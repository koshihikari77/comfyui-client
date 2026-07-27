# scene_id をファイル名に自動注入する

## 背景

生成画像のファイル名に scene_id（`scene_delta._id`）を入れたい。投稿前の整理・同定・DB 不要での scene 特定のため。

現状はファイル名から scene_id が分からず、毎案件で SQLite を引いて事後 rename している（手間 + ヒューマンエラー）。

## 現状の挙動（2026-04-30 時点）

### サーバー側 ComfyUI

- `SaveImage` ノード（base.json では node 318）の `filename_prefix` を見てサブディレクトリ込みで保存する
- 例: `filename_prefix="lize_natsumatsuri/00_intro_festival"` → `output/lize_natsumatsuri/00_intro_festival_00001_.png` を出力
- 動作自体は仕様通り

### ComfyV 側

- `core/executors/base_executor.py:_execute_single_run` で次の通り：
  ```python
  image_save_path = self.results_images_dir / f"{image_id:08d}.png"
  ```
- ComfyUI からは API 経由で **画像バイナリだけ** を取得し、ComfyV が独自に `results/images/{image_id:08d}.png` で保存し直す
- ComfyUI の `filename_prefix` で決まったサーバー側ファイル名は **完全に無視**される
- DB の `images` テーブルには `parameters` 列に `318.filename_prefix` が記録されているので**事後参照は可能**

### 結果としての症状

- `results/images/00012195.png` のような数値だけのファイル名で蓄積
- 後段の `postprocess/reorder_images` でも `{order:02d}_{image_id:08d}.png` になり scene_id は付かない
- 投稿前に scene 特定したい時、SQLite から `parameters.318.filename_prefix` を引いて手で rename する運用になっている

### 既存の job.yaml 側ワークアラウンド

`scene_delta._params` に毎シーン以下を書いている案件がある：

```yaml
- { node_id: 318, input_name: "filename_prefix", value: "<job>/<scene_id>" }
```

これは **DB の parameters に記録される**ためには有効だが、**ファイル名には反映されない**（ComfyV が破棄するため）。実質「DB 用のメモ」になっており、本来の目的（ファイル名で scene 特定）には届いていない。

## 修正案

### 方針

`scene._id` は ComfyV が既に保持している情報なので、それを **base_executor のファイル保存名に直接注入する**。`_params` で SaveImage の `filename_prefix` を書く必要はなくす。

### 仕様

- 保存ファイル名: `{image_id:08d}_{scene_id}.png`
  - 例: `00012195_00_intro_festival.png`
- `scene_id` が無い場合（grid_search 等）は従来どおり `{image_id:08d}.png`
- 既存の reorder_images は順序は変えるが scene_id 付きファイル名は維持されるため互換性あり

### 修正箇所

#### 1. `core/executors/base_executor.py`

```python
def _execute_single_run(self, job_id, workflow, params, scene_id: str | None = None):
    image_id = self.db.create_image_record(job_id, workflow, params)
    try:
        prompt_id = self.api.queue_prompt(workflow)
        self.api.wait_for_completion(prompt_id)
        result = self.api.get_generated_image(prompt_id)
        if not result:
            raise RuntimeError("Failed to get generated image from history.")
        _, image_data = result

        suffix = f"_{scene_id}" if scene_id else ""
        image_save_path = self.results_images_dir / f"{image_id:08d}{suffix}.png"
        with open(image_save_path, "wb") as f:
            f.write(image_data)

        db_filepath = os.path.join('results', 'images', f"{image_id:08d}{suffix}.png")
        self.db.update_image_record(image_id, db_filepath, 'success')
        return True
    except Exception as e:
        self.db.update_image_record(image_id, None, 'failed')
        logger.error(f"Single run failed for image_id {image_id}", exc_info=True)
        return False
```

#### 2. `core/executors/sequence_executor.py`

scene を回しているループで `scene["_id"]` を `_execute_single_run` に渡すよう修正。

```python
scene_id = scene.get("_id")
self._execute_single_run(job_id, workflow, params, scene_id=scene_id)
```

#### 3. `core/executors/grid_search_executor.py` 等

scene_id 概念がない executor は現行どおり（`scene_id=None`）。

### 影響範囲

| 影響 | 内容 |
|---|---|
| 既存生成画像 | 不変（過去の `00012195.png` はそのまま） |
| 新規生成画像 | `{image_id}_{scene_id}.png` 形式に変わる |
| 既存 job.yaml の `_params filename_prefix` | **無害**（DB に記録されるだけ、ファイル名は ComfyV の方が優先）削除しても残しても OK |
| `postprocess/reorder_images` | 入力ファイル名が変わっても動作する（連番 prefix を付けるだけ）。出力は `{order}_{image_id}_{scene_id}.png` 形式に |
| `postprocess/remove_meta` (`meta-strip`) | ファイル名そのまま `.jpg` に変換するので影響なし |
| DB schema | 変更なし（`filepath` は文字列） |

### 移行

- 既存案件: そのまま動作。事後 rename スクリプトは継続使用可（不要になるが残しても害はない）
- 新規案件: 修正後の ComfyV を使えば自動で scene_id 付与される。job.yaml に `node 318 filename_prefix` を書く必要なし
- 推奨: 修正完了後、新規 job テンプレからは `node 318 filename_prefix` 行を削除

### テスト

- sequence job を実行 → `results/images/{image_id}_{scene_id}.png` 形式で保存されることを確認
- grid_search job を実行 → 従来通り `{image_id}.png` で保存されることを確認
- DB の `filepath` カラムが新形式になっていることを確認

## 関連

- `core/executors/base_executor.py:155-178` 修正対象
- `core/executors/sequence_executor.py` の scene ループ
- 案件側 `pixiv/wakame/*/job.yaml` の `_params node 318 filename_prefix` は順次削除可
- `pixiv/wakame/20260430_リゼ夏祭り/` で実例ベース（既に `_params` で書いているがファイル名には未反映）
