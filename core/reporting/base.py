"""
Base classes and data structures for reporting
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any


@dataclass
class ImageData:
    """画像データの情報を保持するクラス"""
    id: int
    filepath: str
    variable_value: Any
    status: str = "success"


@dataclass 
class JobReportData:
    """ジョブレポートに必要なデータを保持するクラス"""
    job_id: int
    job_name: str
    images: List[ImageData]
    variables: List[Dict[str, Any]]
    variable_name: str  # 表示用の変数名（最初の変数）


class BaseReportGenerator(ABC):
    """レポート生成の抽象基底クラス"""
    
    @abstractmethod
    def generate(self, job_data: JobReportData, output_path: Path) -> None:
        """
        レポートを生成する
        
        Args:
            job_data: ジョブのレポートデータ
            output_path: 出力パス
        """
        pass