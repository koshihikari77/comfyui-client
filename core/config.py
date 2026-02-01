import yaml
import logging
import copy
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from pydantic import ValidationError

from .schemas.config_models import JobConfigModel, ConnectionConfigModel

logger = logging.getLogger(__name__)


# =============================================================================
# scene_delta コンパイラ
# =============================================================================

def _substitute_constants_in_text(text: str, constants: Optional[Dict[str, Any]]) -> str:
    """
    %name% 記法を constants で置換する（scene_delta コンパイル用）。
    list定数は ", ".join(list) にして展開する。
    """
    if not constants:
        return text

    pattern = r'%([a-zA-Z_][a-zA-Z0-9_]*)%'

    def replace_constant(match: re.Match) -> str:
        name = match.group(1)
        if name not in constants:
            return match.group(0)
        val = constants[name]
        return ", ".join(val) if isinstance(val, list) else str(val)

    return re.sub(pattern, replace_constant, text)


def _normalize_slot_value(value: Any, constants: Optional[Dict[str, Any]] = None) -> Optional[List[str]]:
    """
    slotの値を List[str] | None に正規化する。
    - null → None
    - List[str] → 空でない要素のみ
    - str → カンマ区切りで分割してリスト化
    """
    if value is None:
        return None
    if isinstance(value, list):
        out: List[str] = []
        for v in value:
            if not isinstance(v, str):
                continue
            s = v.strip()
            if not s:
                continue
            s = _substitute_constants_in_text(s, constants)
            out.append(s.strip())
        return out
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        s = _substitute_constants_in_text(s, constants)
        return [part.strip() for part in s.split(',') if part.strip()]
    return None


def compile_scene_delta(job_raw_data: dict) -> dict:
    """
    scene_delta 記法を従来の prompts 形式にコンパイルする。
    
    scene_delta は差分ベースでプロンプトを記述できる拡張記法:
    - 基本形: { slotA: value, slotB: [tag1, tag2] } は set と同義
    - 予約キー:
      - _id: 任意ID（未指定なら自動連番）
      - _from: 参照元（"base" = 初期テンプレ, ID = そのIDのstate, 省略 = 直前state）
      - _unset: List[str]（slotを出力から除外）
      - _add: Dict[str, str|List[str]]（slotにタグを追加）
      - _del: Dict[str, str|List[str]]（slotからタグを完全一致で削除）
      - _params: List[{node_id, input_name, value}]（ワークフローパラメータ。set→以後継承）
      - _runs: int（このpromptだけのruns指定）
      - _name: str（prompt名）
    - slotの値は内部的に常に List[str]|None に正規化される（str はカンマ区切りで分割）
    
    Args:
        job_raw_data: 読み込んだjob config辞書
        
    Returns:
        scene_delta がコンパイルされた job_raw_data（元データを変更しない）
        
    Raises:
        ValueError: prompts_delta が指定されている場合（scene_delta を使用してください）
        ValueError: prompts と scene_delta が両方存在する場合
        ValueError: prompt_template が無いのに scene_delta がある場合
        ValueError: _from で参照したIDが存在しない場合
    """
    has_prompts = bool(job_raw_data.get('prompts'))
    has_prompts_delta = bool(job_raw_data.get('prompts_delta'))
    has_scene_delta = bool(job_raw_data.get('scene_delta'))
    
    if has_prompts_delta:
        raise ValueError("'prompts_delta' は廃止されました。'scene_delta' を使用してください。")
    
    if has_prompts and has_scene_delta:
        raise ValueError("'prompts' と 'scene_delta' は同時に指定できません。どちらか一方を使用してください。")
    
    if not has_scene_delta:
        return job_raw_data
    
    prompt_template = job_raw_data.get('prompt_template')
    if not prompt_template:
        raise ValueError("'scene_delta' を使用する場合は 'prompt_template' が必須です。")
    
    order = prompt_template.get('order')
    slots = prompt_template.get('slots', {})
    
    if not order:
        raise ValueError("'prompt_template.order' は必須です。")
    
    scene_delta = job_raw_data['scene_delta']
    compiled_prompts = _compile_delta_items(
        scene_delta,
        order,
        slots,
        constants=job_raw_data.get('constants') or {},
    )
    
    result = copy.copy(job_raw_data)
    result['prompts'] = compiled_prompts
    
    return result


def _compile_delta_items(
    delta_items: List[dict],
    order: List[str],
    base_slots: Dict[str, Any],
    *,
    constants: Optional[Dict[str, Any]] = None,
) -> List[dict]:
    """
    差分アイテムのリストをコンパイルしてprompts形式に変換。
    
    Args:
        delta_items: scene_delta のリスト
        order: 出力順序
        base_slots: 初期テンプレートのslots
        
    Returns:
        List[dict]: 各要素は {template, runs?, name?, params?}
    """
    compiled = []
    
    base_normalized: Dict[str, Optional[List[str]]] = {}
    for k, v in base_slots.items():
        base_normalized[k] = _normalize_slot_value(v, constants=constants)
    
    resolved_states: Dict[str, Dict[str, Optional[List[str]]]] = {}
    resolved_states['base'] = copy.deepcopy(base_normalized)
    prev_state: Dict[str, Optional[List[str]]] = copy.deepcopy(base_normalized)
    param_state: Dict[str, dict] = {}
    
    for idx, item in enumerate(delta_items):
        item_id = item.get('_id', str(idx))
        from_ref = item.get('_from')
        unset_keys = item.get('_unset', [])
        add_dict = item.get('_add', {})
        del_dict = item.get('_del', {})
        params_list = item.get('_params', [])
        runs = item.get('_runs')
        name = item.get('_name')
        
        if from_ref is not None:
            if from_ref == 'base':
                current_state = copy.deepcopy(base_normalized)
            elif from_ref in resolved_states:
                current_state = copy.deepcopy(resolved_states[from_ref])
            else:
                raise ValueError(f"scene_delta[{idx}]: _from で参照した ID '{from_ref}' は存在しません。")
        else:
            current_state = copy.deepcopy(prev_state)
        
        # set: 予約キー以外のキーを上書き（正規化して List[str]|None）
        for key, value in item.items():
            if not key.startswith('_'):
                current_state[key] = _normalize_slot_value(value, constants=constants)
        
        for key in unset_keys:
            current_state[key] = None
        
        # _add: タグを追加
        for key, add_value in add_dict.items():
            existing = current_state.get(key)
            if existing is None:
                existing = []
            else:
                existing = list(existing)
            to_add = _normalize_slot_value(add_value, constants=constants)
            if to_add:
                existing.extend(to_add)
            current_state[key] = existing
        
        # _del: 完全一致でタグを削除
        for key, del_value in del_dict.items():
            existing = current_state.get(key)
            if existing is None or not isinstance(existing, list):
                continue
            to_remove = _normalize_slot_value(del_value, constants=constants)
            if not to_remove:
                continue
            remove_set = set(to_remove)
            current_state[key] = [t for t in existing if t not in remove_set]
        
        # _params: ワークフローパラメータを更新（set→以後継承）
        for p in params_list:
            if not isinstance(p, dict):
                continue
            nid = p.get('node_id')
            iname = p.get('input_name')
            val = p.get('value')
            if nid is None or iname is None:
                continue
            key = f"{nid}.{iname}"
            param_state[key] = {'node_id': nid, 'input_name': iname, 'value': val}
        
        resolved_states[str(item_id)] = copy.deepcopy(current_state)
        prev_state = copy.deepcopy(current_state)
        
        flat_tags = _flatten_state_to_tags(current_state, order)
        prompt_item = {'template': ', '.join(flat_tags)}
        if runs is not None:
            prompt_item['runs'] = runs
        if name is not None:
            prompt_item['name'] = name
        if param_state:
            prompt_item['params'] = list(param_state.values())
        compiled.append(prompt_item)
    
    return compiled


def _flatten_state_to_tags(state: Dict[str, Optional[List[str]]], order: List[str]) -> List[str]:
    """
    stateをorderに従ってフラットなタグリストに変換。
    stateの値は常に List[str]|None に正規化されている前提。
    """
    tags = []
    for slot_name in order:
        value = state.get(slot_name)
        if value is None:
            continue
        for v in value:
            if v and isinstance(v, str):
                tags.append(v)
    return tags

class Config:
    def __init__(self, job_config_path: str, connection_config_path: str):
        self.job_config_path = Path(job_config_path)
        self.connection_config_path = Path(connection_config_path)
        
        # ファイルの存在確認
        if not self.job_config_path.exists():
            raise FileNotFoundError(f"Job config file not found: {job_config_path}")
        if not self.connection_config_path.exists():
            raise FileNotFoundError(f"Connection config file not found: {connection_config_path}")
        
        # 設定ファイルを読み込み
        job_raw_data = self._load_yaml(self.job_config_path)
        connection_raw_data = self._load_yaml(self.connection_config_path)
        
        # scene_delta をコンパイル（Pydantic検証前に実行）
        job_raw_data = compile_scene_delta(job_raw_data)
        
        # Pydanticモデルでバリデーション
        self._validate_with_pydantic(job_raw_data, connection_raw_data)
        
        # 後方互換性のため、元のデータも保持
        self.job_data = job_raw_data
        self.connection_data = connection_raw_data

    def _validate_with_pydantic(self, job_raw_data: dict, connection_raw_data: dict):
        """Pydanticモデルを使用してバリデーション"""
        try:
            # ジョブ設定のバリデーション
            self.job_config_model = JobConfigModel(**job_raw_data)
            logger.debug(f"Job config validation successful: {self.job_config_model.job_name}")
            
            # 接続設定のバリデーション
            self.connection_config_model = ConnectionConfigModel(**connection_raw_data)
            logger.debug(f"Connection config validation successful: {self.connection_config_model.server_address}")
            
        except ValidationError as e:
            # PydanticのValidationErrorを従来のエラー形式に変換（後方互換性のため）
            error_str = str(e)
            
            # 特定のエラーパターンを既存のメッセージ形式に変換
            if 'base_workflow' in error_str and '必須です' in error_str:
                raise ValueError("Missing required key in config: 'base_workflow'")
            elif 'variables' in error_str and 'list' in error_str:
                raise TypeError("'variables' must be a list.")
            elif 'Field required' in error_str and 'variables' in error_str:
                if 'input_name' in error_str:
                    raise ValueError("Missing required key in 'variable': 'input_name'")
                elif 'values' in error_str:
                    raise ValueError("Missing required key in 'variable': 'values'")
            elif 'server_address' in error_str:
                # server_addressのバリデーションエラーを適切に処理
                error_messages = []
                for error in e.errors():
                    if 'server_address' in str(error.get('loc', [])):
                        error_messages.append(error['msg'])
                if error_messages:
                    # バリデーションエラー（形式不正）
                    if 'Value error' in error_str or 'value_error' in error_str.lower():
                        raise ValueError(f"server_addressは有効なURL形式: {error_messages[0]}")
                    # 必須フィールドエラー
                    raise ValueError("Missing required key in connection config: 'server_address'")
                raise ValueError("Missing required key in connection config: 'server_address'")
            
            # デフォルトケース: より詳細なエラーメッセージ
            error_messages = []
            for error in e.errors():
                field_path = '.'.join(str(loc) for loc in error['loc'])
                error_messages.append(f"Field '{field_path}': {error['msg']}")
            
            # prompts, iteratorsのエラーも適切に処理
            if 'prompts' in error_str and ('無効なプロンプト形式' in error_str or 'model_type' in error_str.lower()):
                raise ValueError(f"無効なプロンプト形式: {'; '.join(error_messages)}")
            elif 'iterators' in error_str and ('空でないリスト' in error_str or 'value_error' in error_str.lower()):
                raise ValueError(f"Iterator設定エラー: {'; '.join(error_messages)}")
            elif 'variables' in error_str or 'job_name' in error_str or 'base_workflow' in error_str or 'parameter_combinations' in error_str:
                raise ValueError(f"Config validation failed: {'; '.join(error_messages)}")
            elif 'server_address' in error_str:
                raise ValueError(f"Connection config validation failed: {'; '.join(error_messages)}")
            else:
                raise TypeError(f"Type validation failed: {'; '.join(error_messages)}")
    
    def _validate(self):
        """既存のメソッド（後方互換性のため保持、内部でPydanticを使用）"""
        # Pydanticバリデーションが既に実行されているので、何もしない
        pass

    def _load_yaml(self, file_path: Path) -> dict:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"YAML parsing error in {file_path}: {e}")
        except Exception as e:
            raise IOError(f"Error reading {file_path}: {e}")

    @property
    def job_name(self) -> str:
        return self.job_data['job_name']

    @property
    def server_address(self) -> str:
        return self.connection_data['server_address']

    @property
    def variables(self) -> list:
        return self.job_config_model.variables

    @property
    def prompts(self) -> list:
        """シーケンスジョブ用のプロンプト定義（正規化済みPromptModelオブジェクト）"""
        return self.job_config_model.prompts

    @property
    def default_runs(self) -> int:
        """デフォルト実行回数"""
        return self.job_config_model.default_runs

    @property
    def iterators(self) -> dict:
        """Iterator定義"""
        return self.job_config_model.iterators

    @property
    def constants(self) -> dict:
        """Constant定義"""
        return self.job_config_model.constants

    @property
    def parameter_combinations(self) -> list:
        """Parameter combinations定義"""
        return self.job_config_model.parameter_combinations

    @property
    def placeholders(self) -> dict:
        return self.job_data.get('placeholders', {})

    @property
    def job_config_data(self) -> dict:
        return self.job_data

    @property
    def fixed_parameters(self) -> list:
        """固定パラメータ（Pydanticモデルのリスト）"""
        return self.job_config_model.fixed_parameters

    @property
    def random_parameters(self) -> list:
        """ランダムパラメータ（Pydanticモデルのリスト）"""
        return self.job_config_model.random_parameters

    @property
    def ignore_tags(self) -> list:
        """無視するタグリスト（PromptResolver設定）"""
        return self.job_config_model.ignore_tags or []

    @property
    def ignore_groups(self) -> list:
        """無視するグループリスト（PromptResolver設定）"""
        return self.job_config_model.ignore_groups or []

    @property
    def locale(self) -> str:
        """区切り文字（PromptResolver設定）"""
        return self.job_config_model.locale or ","

    @property
    def strict_level(self) -> str:
        """エラー処理レベル（PromptResolver設定）"""
        return self.job_config_model.strict_level or "warn"

    @property
    def seed(self) -> int:
        """乱数シード（PromptResolver設定）"""
        return self.job_config_model.seed

    @property
    def base_workflow_path(self) -> Path:
        if 'base_workflow' not in self.job_data:
            return None
        
        workflow_filename = self.job_data['base_workflow']
        
        # 絶対パスまたは相対パスで直接指定されている場合
        if Path(workflow_filename).is_absolute():
            return Path(workflow_filename)
        
        # 相対パスの場合の解決
        # 1. 標準的なディレクトリ構造の場合を優先
        # job_config_path が configs/jobs/**/xxx.yaml の場合、
        # configs/ ディレクトリ（jobs/ の親）を基準にする
        for parent in self.job_config_path.parents:
            if parent.name == 'jobs':
                configs_dir = parent.parent
                return configs_dir / workflow_filename
            
        # 2. job_config_pathと同じディレクトリにある場合（フラットな構造のテスト用）
        same_dir_path = self.job_config_path.parent / workflow_filename
        return same_dir_path