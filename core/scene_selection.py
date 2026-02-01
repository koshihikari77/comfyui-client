from __future__ import annotations

import re
from typing import Dict, List, Tuple


def extract_scene_delta_id_index_map(job_raw_data: dict) -> Tuple[List[str], Dict[str, int]]:
    """
    scene_delta の配列から index -> id と id -> index を返す。
    _id が無い場合は compiler と同様に str(index) を ID とみなす。
    """
    scene_delta = job_raw_data.get("scene_delta")
    if not isinstance(scene_delta, list):
        raise ValueError("scene_delta が見つかりません（--scenes は scene_delta ベース専用）")
    ids_by_index: List[str] = []
    index_by_id: Dict[str, int] = {}
    for idx, item in enumerate(scene_delta):
        if isinstance(item, dict) and "_id" in item and item["_id"] is not None:
            scene_id = str(item["_id"])
        else:
            scene_id = str(idx)
        ids_by_index.append(scene_id)
        index_by_id[scene_id] = idx
    return ids_by_index, index_by_id


def parse_scene_selection(spec: str, index_by_id: Dict[str, int], max_index: int) -> List[int]:
    """
    --scenes の指定文字列を index のリストに変換する。
    対応形式:
      - 数字: "0"
      - 範囲: "3-5"（両端含む）
      - ID: "base_sitting"
      - カンマ区切り: "0,2,base_sitting,5-12"
    """
    if spec is None:
        return []
    tokens = [t.strip() for t in spec.split(",") if t.strip()]
    if not tokens:
        return []

    selected: List[int] = []
    for token in tokens:
        range_match = re.match(r"^(\d+)\s*-\s*(\d+)$", token)
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2))
            if start > end:
                raise ValueError(f"--scenes の範囲指定が不正です: {token}")
            if start < 0 or end >= max_index:
                raise ValueError(f"--scenes の範囲指定が範囲外です: {token}")
            selected.extend(range(start, end + 1))
            continue

        if token.isdigit():
            idx = int(token)
            if idx < 0 or idx >= max_index:
                raise ValueError(f"--scenes の index が範囲外です: {token}")
            selected.append(idx)
            continue

        if token in index_by_id:
            selected.append(index_by_id[token])
            continue

        raise ValueError(f"--scenes の指定が不正です（ID が見つかりません）: {token}")

    # 重複排除しつつ index 昇順（実行順を維持）
    return sorted(set(selected))


def filter_config_prompts_inplace(config, selected_indices: List[int]) -> None:
    """
    Config の prompts を index で絞り込む（in-place）。
    - config.job_config_model.prompts
    - config.job_data['prompts']（存在する場合）
    """
    if not selected_indices:
        return
    config.job_config_model.prompts = [
        p for i, p in enumerate(config.job_config_model.prompts) if i in selected_indices
    ]
    if isinstance(config.job_data, dict) and "prompts" in config.job_data:
        config.job_data["prompts"] = [
            p for i, p in enumerate(config.job_data["prompts"]) if i in selected_indices
        ]
