import yaml
import pytest

from core.config import Config
from core.scene_selection import (
    extract_scene_delta_id_index_map,
    filter_config_prompts_inplace,
    parse_scene_selection,
)


def test_parse_scene_selection_mixed_spec():
    index_by_id = {"base": 1, "foo": 4}
    selected = parse_scene_selection("0,2,base,5-6", index_by_id=index_by_id, max_index=7)
    assert selected == [0, 1, 2, 5, 6]


def test_parse_scene_selection_invalid_id():
    index_by_id = {"base": 1}
    with pytest.raises(ValueError, match="ID が見つかりません"):
        parse_scene_selection("unknown", index_by_id=index_by_id, max_index=3)


def test_parse_scene_selection_out_of_range():
    index_by_id = {}
    with pytest.raises(ValueError, match="範囲外"):
        parse_scene_selection("10", index_by_id=index_by_id, max_index=3)


def test_parse_scene_selection_start_only_index():
    """6- が [6..max-1] になる"""
    index_by_id = {}
    selected = parse_scene_selection("6-", index_by_id=index_by_id, max_index=10)
    assert selected == [6, 7, 8, 9]


def test_parse_scene_selection_end_only_index():
    """-6 が [0..6] になる"""
    index_by_id = {}
    selected = parse_scene_selection("-6", index_by_id=index_by_id, max_index=10)
    assert selected == [0, 1, 2, 3, 4, 5, 6]


def test_parse_scene_selection_start_only_id():
    """id- が id→index 解決され [start..max-1] になる"""
    index_by_id = {"base": 1, "foo": 4}
    selected = parse_scene_selection("base-", index_by_id=index_by_id, max_index=7)
    assert selected == [1, 2, 3, 4, 5, 6]


def test_parse_scene_selection_end_only_id():
    """-id が id→index 解決され [0..end] になる"""
    index_by_id = {"base": 1, "foo": 4}
    selected = parse_scene_selection("-foo", index_by_id=index_by_id, max_index=7)
    assert selected == [0, 1, 2, 3, 4]


def test_parse_scene_selection_mixed_with_open_ranges():
    """既存 spec と開区間の混在"""
    index_by_id = {"mid": 2}
    selected = parse_scene_selection("0, 2-3, mid-, -1", index_by_id=index_by_id, max_index=5)
    # 0, 2, 3, mid-(2,3,4), -1(0,1) → 0,1,2,3,4
    assert selected == [0, 1, 2, 3, 4]


def test_filter_prompts_by_scene_id(temp_config_dir, sample_connection_config):
    jobs_dir = temp_config_dir / "jobs"
    jobs_dir.mkdir()

    config_data = {
        "job_name": "scene_delta_filter",
        "job_type": "sequence",
        "prompt_template": {
            "order": ["subject"],
            "slots": {"subject": "base"},
        },
        "scene_delta": [
            {"_id": "scene_a", "subject": "a"},
            {"_id": "scene_b", "subject": "b"},
            {"_id": "scene_c", "subject": "c"},
        ],
    }

    config_path = jobs_dir / "scene_delta_filter.yaml"
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config_data, f, default_flow_style=False)

    config = Config(
        job_config_path=str(config_path),
        connection_config_path=str(sample_connection_config),
    )

    ids_by_index, index_by_id = extract_scene_delta_id_index_map(config.job_data)
    selected = parse_scene_selection("scene_b", index_by_id=index_by_id, max_index=len(ids_by_index))
    filter_config_prompts_inplace(config, selected)

    assert len(config.prompts) == 1
    assert config.prompts[0].template == "b"
