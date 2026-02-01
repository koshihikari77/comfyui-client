"""
Pydantic models for configuration validation
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Dict, Any, Optional, Union, Literal
from enum import Enum


class JobTypeEnum(str, Enum):
    """ジョブタイプの列挙型"""
    GRID_SEARCH = "grid_search"
    SEQUENCE = "sequence"


class VariableModel(BaseModel):
    """変数定義のモデル"""
    node_id: Union[int, str] = Field(..., description="ワークフローのノードIDまたはノード名")
    input_name: str = Field(..., min_length=1, description="入力パラメータ名")
    values: List[Any] = Field(..., min_length=1, description="値のリスト")

    @field_validator('node_id')
    @classmethod
    def validate_node_id(cls, v):
        if isinstance(v, int):
            if v <= 0:
                raise ValueError("node_idは正の整数である必要があります")
        elif isinstance(v, str):
            if not v.strip():
                raise ValueError("node_id（ノード名）は空文字列ではいけません")
        else:
            raise ValueError("node_idは整数または文字列である必要があります")
        return v


class FixedParameterModel(BaseModel):
    """固定パラメータのモデル"""
    node_id: Union[int, str] = Field(..., description="ワークフローのノードIDまたはノード名")
    input_name: str = Field(..., min_length=1, description="入力パラメータ名")
    value: Optional[Any] = Field(None, description="固定値（単一値）")
    values: Optional[List[Any]] = Field(None, description="固定値（リスト形式）")

    @field_validator('node_id')
    @classmethod
    def validate_node_id(cls, v):
        if isinstance(v, int):
            if v <= 0:
                raise ValueError("node_idは正の整数である必要があります")
        elif isinstance(v, str):
            if not v.strip():
                raise ValueError("node_id（ノード名）は空文字列ではいけません")
        else:
            raise ValueError("node_idは整数または文字列である必要があります")
        return v

    @model_validator(mode='after')
    def validate_value_or_values(self):
        """valueかvaluesのどちらか一つが必須"""
        if self.value is None and self.values is None:
            raise ValueError("valueまたはvaluesのどちらか一つは必須です")
        if self.value is not None and self.values is not None:
            raise ValueError("valueとvaluesは同時に指定できません")
        return self


class RandomParameterModel(BaseModel):
    """ランダムパラメータのモデル"""
    node_id: Union[int, str] = Field(..., description="ワークフローのノードIDまたはノード名")
    input_name: str = Field(..., min_length=1, description="入力パラメータ名")
    type: str = Field(default="float", description="値の型")
    
    # 範囲指定用（type: int用）
    range: Optional[List[Union[int, float]]] = Field(None, description="値の範囲 [min, max]")
    
    # 選択肢指定用（type: choice用）
    values: Optional[List[Union[int, float, str]]] = Field(None, description="選択肢のリスト")

    @field_validator('node_id')
    @classmethod
    def validate_node_id(cls, v):
        if isinstance(v, int):
            if v <= 0:
                raise ValueError("node_idは正の整数である必要があります")
        elif isinstance(v, str):
            if not v.strip():
                raise ValueError("node_id（ノード名）は空文字列ではいけません")
        else:
            raise ValueError("node_idは整数または文字列である必要があります")
        return v

    @model_validator(mode='after')
    def validate_parameters(self):
        if self.type == 'choice':
            if not self.values:
                raise ValueError("type='choice'の場合、valuesは必須です")
        elif self.type == 'int':
            if not self.range:
                raise ValueError("type='int'の場合、rangeは必須です")
            if len(self.range) != 2:
                raise ValueError("rangeは[min, max]の形式で指定してください")
            if self.range[0] >= self.range[1]:
                raise ValueError("range[0]はrange[1]より小さい必要があります")
        return self


class IteratorItemModel(BaseModel):
    """Iterator項目定義（expand_preset用）"""
    expand_preset: str = Field(..., min_length=1, description="展開するプリセット名")


class ParameterItemModel(BaseModel):
    """パラメータ組み合わせの個別項目"""
    node_id: Union[int, str] = Field(..., description="ワークフローのノードIDまたはノード名")
    input_name: str = Field(..., min_length=1, description="入力パラメータ名")
    value: Union[int, float, str] = Field(..., description="パラメータ値")

    @field_validator('node_id')
    @classmethod
    def validate_node_id(cls, v):
        if isinstance(v, int):
            if v <= 0:
                raise ValueError("node_idは正の整数である必要があります")
        elif isinstance(v, str):
            if not v.strip():
                raise ValueError("node_id（ノード名）は空文字列ではいけません")
        else:
            raise ValueError("node_idは整数または文字列である必要があります")
        return v


class ParameterCombinationModel(BaseModel):
    """パラメータ組み合わせ定義"""
    name: str = Field(..., min_length=1, description="組み合わせの識別名")
    parameters: List[ParameterItemModel] = Field(..., min_length=1, description="パラメータのリスト")

    @field_validator('parameters')
    @classmethod
    def validate_unique_parameters(cls, v):
        """同一の node_id.input_name の重複をチェック"""
        seen = set()
        for param in v:
            key = f"{param.node_id}.{param.input_name}"
            if key in seen:
                raise ValueError(f"重複するパラメータが検出されました: node_id={param.node_id}, input_name={param.input_name}")
            seen.add(key)
        return v


class SceneParamItemModel(BaseModel):
    """scene_delta 由来のワークフローパラメータ（set→以後継承）。value は任意型。"""
    node_id: Union[int, str] = Field(..., description="ワークフローのノードIDまたはノード名")
    input_name: str = Field(..., min_length=1, description="入力パラメータ名")
    value: Any = Field(None, description="パラメータ値（任意型）")

    @field_validator('node_id')
    @classmethod
    def validate_node_id(cls, v):
        if isinstance(v, int):
            if v <= 0:
                raise ValueError("node_idは正の整数である必要があります")
        elif isinstance(v, str):
            if not v.strip():
                raise ValueError("node_id（ノード名）は空文字列ではいけません")
        else:
            raise ValueError("node_idは整数または文字列である必要があります")
        return v


class PromptModel(BaseModel):
    """プロンプト定義のモデル（シーケンス用）"""
    template: str = Field(..., min_length=1, description="プロンプトテンプレート")
    runs: Optional[int] = Field(None, description="実行回数")
    name: Optional[str] = Field(None, description="プロンプト名")
    params: Optional[List[SceneParamItemModel]] = Field(default=None, description="scene_delta由来のワークフローパラメータ（set→以後継承）")


class JobConfigModel(BaseModel):
    """ジョブ設定のメインモデル"""
    job_name: str = Field(..., min_length=1, description="ジョブ名")
    job_type: JobTypeEnum = Field(default=JobTypeEnum.GRID_SEARCH, description="ジョブタイプ")
    base_workflow: Optional[str] = Field(None, description="ベースワークフローファイル")
    
    # PromptResolver設定（設計書§4.1.1）
    ignore_tags: Optional[List[str]] = Field(default=[], description="無視するタグリスト")
    ignore_groups: Optional[List[str]] = Field(default=[], description="無視するグループリスト")
    locale: Optional[Literal[",", "、", ";"]] = Field(default=",", description="区切り文字")
    strict_level: Optional[Literal["soft", "warn", "error"]] = Field(default="warn", description="エラー処理レベル")
    seed: Optional[int] = Field(default=None, description="乱数シード")
    
    # グリッドサーチ用
    variables: List[VariableModel] = Field(default=[], description="変数定義")
    placeholders: Dict[str, List[str]] = Field(default={}, description="プレースホルダー定義")
    fixed_parameters: List[FixedParameterModel] = Field(default=[], description="固定パラメータ")
    random_parameters: List[RandomParameterModel] = Field(default=[], description="ランダムパラメータ")
    
    # シーケンス用
    default_runs: Optional[int] = Field(default=1, description="デフォルトrun数")
    prompts: List[Union[PromptModel, List[str], Dict[str, Any]]] = Field(default=[], description="プロンプト定義（シーケンス用）")
    iterators: Optional[Dict[str, Union[List[str], Dict[str, str]]]] = Field(default={}, description="Iterator定義（手動リストまたはexpand_preset指示）")
    constants: Optional[Dict[str, Union[str, List[str]]]] = Field(default={}, description="定数定義（%constant_name%記法で参照。値はstrまたはList[str]）")
    parameter_combinations: Optional[List[ParameterCombinationModel]] = Field(default=[], description="パラメータ組み合わせ定義（実行時に順次適用）")

    @model_validator(mode='after')
    def validate_job_type_requirements(self):
        """ジョブタイプに応じた必須フィールドをチェック"""
        if self.job_type == JobTypeEnum.GRID_SEARCH:
            if not self.base_workflow:
                raise ValueError("grid_searchジョブではbase_workflowが必須です")
            if not self.variables:
                raise ValueError("grid_searchジョブではvariablesが必須です")
        
        elif self.job_type == JobTypeEnum.SEQUENCE:
            if not self.prompts:
                raise ValueError("sequenceジョブではpromptsが必須です")
        
        return self

    @model_validator(mode='after')
    def normalize_prompts(self):
        """プロンプト形式を正規化"""
        if not self.prompts:
            return self
        
        normalized = []
        for item in self.prompts:
            if isinstance(item, list):  # List[str] -> PromptModel
                template = ", ".join(item)
                normalized.append(PromptModel(
                    template=template,
                    runs=None  # default_runsを使用
                ))
            elif isinstance(item, dict):  # 既存形式
                normalized.append(PromptModel(**item))
            elif isinstance(item, PromptModel):  # 既にモデル化済み
                normalized.append(item)
            else:
                raise ValueError(f"無効なプロンプト形式: {type(item)}")
        
        self.prompts = normalized
        return self
    
    @field_validator('placeholders')
    @classmethod
    def validate_placeholders(cls, v):
        """プレースホルダーの値が空でないリストであることを確認"""
        for key, values in v.items():
            if not isinstance(values, list) or len(values) == 0:
                raise ValueError(f"プレースホルダー '{key}' は空でないリストである必要があります")
        return v

    @field_validator('iterators')
    @classmethod
    def validate_iterators(cls, v):
        """Iterator定義の形式チェック"""
        if not v:  # 空の場合はOK
            return v
        
        for iterator_name, iterator_value in v.items():
            if isinstance(iterator_value, list):
                # 手動リスト定義の場合
                if len(iterator_value) == 0:
                    raise ValueError(f"Iterator '{iterator_name}' は空でないリストである必要があります")
                for item in iterator_value:
                    if not isinstance(item, str):
                        raise ValueError(f"Iterator '{iterator_name}' のリスト要素は文字列である必要があります")
            elif isinstance(iterator_value, dict):
                # expand_preset指示の場合
                if 'expand_preset' not in iterator_value:
                    raise ValueError(f"Iterator '{iterator_name}' の辞書には 'expand_preset' キーが必要です")
                if not isinstance(iterator_value['expand_preset'], str) or len(iterator_value['expand_preset']) == 0:
                    raise ValueError(f"Iterator '{iterator_name}' の 'expand_preset' は空でない文字列である必要があります")
            else:
                raise ValueError(f"Iterator '{iterator_name}' はリストまたは辞書である必要があります")
        
        return v

    @field_validator('constants')
    @classmethod
    def validate_constants(cls, v):
        """Constants定義の形式チェック（値はstrまたはList[str]）"""
        if not v:
            return v
        
        for constant_name, constant_value in v.items():
            if not isinstance(constant_name, str) or len(constant_name) == 0:
                raise ValueError(f"Constant名 '{constant_name}' は空でない文字列である必要があります")
            if isinstance(constant_value, list):
                for item in constant_value:
                    if not isinstance(item, str):
                        raise ValueError(f"Constant '{constant_name}' のリスト要素は文字列である必要があります")
            elif not isinstance(constant_value, str):
                raise ValueError(f"Constant '{constant_name}' の値は文字列または文字列のリストである必要があります")
        
        return v

    @field_validator('parameter_combinations')
    @classmethod
    def validate_parameter_combinations(cls, v):
        """Parameter combinations定義の形式チェック"""
        if not v:  # 空の場合はOK
            return v
        
        combination_names = set()
        for combination in v:
            # 組み合わせ名の重複チェック
            if combination.name in combination_names:
                raise ValueError(f"Parameter combination名 '{combination.name}' が重複しています")
            combination_names.add(combination.name)
        
        return v


class ConnectionConfigModel(BaseModel):
    """接続設定のモデル"""
    server_address: str = Field(..., min_length=1, description="ComfyUIサーバーアドレス")
    timeout: Optional[int] = Field(default=30, gt=0, description="タイムアウト時間（秒）")
    retry_count: Optional[int] = Field(default=3, ge=0, description="リトライ回数")

    @field_validator('server_address')
    @classmethod
    def validate_server_address(cls, v):
        """
        サーバーアドレスの基本的な形式チェック
        
        許可される形式:
        - http://host:port
        - https://host:port
        - host:port
        """
        v = v.strip()
        
        # http://またはhttps://で始まる場合はOK
        if v.startswith('http://') or v.startswith('https://'):
            return v
        
        # host:port形式をチェック
        if ':' in v:
            parts = v.split(':')
            if len(parts) == 2:
                host, port = parts
                # ポート番号が数値かチェック
                try:
                    int(port)
                    return v
                except ValueError:
                    raise ValueError(f"server_addressのポート番号が無効です: {port}")
        
        raise ValueError("server_addressは有効なURL形式（http://host:port または https://host:port）またはhost:port形式である必要があります")