"""
Pydantic models for configuration validation
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Dict, Any, Optional, Union
from enum import Enum


class JobTypeEnum(str, Enum):
    """ジョブタイプの列挙型"""
    GRID_SEARCH = "grid_search"
    SEQUENCE = "sequence"


class VariableModel(BaseModel):
    """変数定義のモデル"""
    node_id: int = Field(..., description="ワークフローのノードID")
    input_name: str = Field(..., min_length=1, description="入力パラメータ名")
    values: List[Any] = Field(..., min_length=1, description="値のリスト")

    @field_validator('node_id')
    @classmethod
    def validate_node_id(cls, v):
        if v <= 0:
            raise ValueError("node_idは正の整数である必要があります")
        return v


class FixedParameterModel(BaseModel):
    """固定パラメータのモデル"""
    node_id: int = Field(..., description="ワークフローのノードID")
    input_name: str = Field(..., min_length=1, description="入力パラメータ名")
    value: Optional[Any] = Field(None, description="固定値（単一値）")
    values: Optional[List[Any]] = Field(None, description="固定値（リスト形式）")

    @field_validator('node_id')
    @classmethod
    def validate_node_id(cls, v):
        if v <= 0:
            raise ValueError("node_idは正の整数である必要があります")
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
    node_id: int = Field(..., description="ワークフローのノードID")
    input_name: str = Field(..., min_length=1, description="入力パラメータ名")
    type: str = Field(default="float", description="値の型")
    
    # 範囲指定用（type: int用）
    range: Optional[List[Union[int, float]]] = Field(None, description="値の範囲 [min, max]")
    
    # 選択肢指定用（type: choice用）
    values: Optional[List[Union[int, float, str]]] = Field(None, description="選択肢のリスト")

    @field_validator('node_id')
    @classmethod
    def validate_node_id(cls, v):
        if v <= 0:
            raise ValueError("node_idは正の整数である必要があります")
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


class PromptModel(BaseModel):
    """プロンプト定義のモデル（シーケンス用）"""
    template: str = Field(..., min_length=1, description="プロンプトテンプレート")
    runs: Optional[int] = Field(None, description="実行回数")
    name: Optional[str] = Field(None, description="プロンプト名")


class JobConfigModel(BaseModel):
    """ジョブ設定のメインモデル"""
    job_name: str = Field(..., min_length=1, description="ジョブ名")
    job_type: JobTypeEnum = Field(default=JobTypeEnum.GRID_SEARCH, description="ジョブタイプ")
    base_workflow: Optional[str] = Field(None, description="ベースワークフローファイル")
    
    # グリッドサーチ用
    variables: List[VariableModel] = Field(default=[], description="変数定義")
    placeholders: Dict[str, List[str]] = Field(default={}, description="プレースホルダー定義")
    fixed_parameters: List[FixedParameterModel] = Field(default=[], description="固定パラメータ")
    random_parameters: List[RandomParameterModel] = Field(default=[], description="ランダムパラメータ")
    
    # シーケンス用
    default_runs: Optional[int] = Field(default=1, description="デフォルトrun数")
    prompts: List[Union[PromptModel, List[str], Dict[str, Any]]] = Field(default=[], description="プロンプト定義（シーケンス用）")

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


class ConnectionConfigModel(BaseModel):
    """接続設定のモデル"""
    server_address: str = Field(..., min_length=1, description="ComfyUIサーバーアドレス")
    timeout: Optional[int] = Field(default=30, gt=0, description="タイムアウト時間（秒）")
    retry_count: Optional[int] = Field(default=3, ge=0, description="リトライ回数")

    @field_validator('server_address')
    @classmethod
    def validate_server_address(cls, v):
        """サーバーアドレスの基本的な形式チェック"""
        if not (v.startswith('http://') or v.startswith('https://') or ':' in v):
            raise ValueError("server_addressは有効なURL形式またはhost:port形式である必要があります")
        return v