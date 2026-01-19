"""
Reporter facade class for unified reporting interface
"""

import json
import os
import logging
from pathlib import Path
from typing import List, Dict, Any

from .base import JobReportData, ImageData
from .html import HTMLReportGenerator

logger = logging.getLogger(__name__)


class Reporter:
    """レポート生成の統一インターフェース"""
    
    def __init__(self, template_dir: str = "templates"):
        """
        Reporterを初期化
        
        Args:
            template_dir: テンプレートファイルのディレクトリ
        """
        self.html_generator = HTMLReportGenerator(template_dir)
        logger.debug("Reporter initialized")
    
    def generate_html_report(self, job_id: int, job_name: str, image_records: List[Dict], 
                           variables: List[Dict], output_dir: str = "results") -> None:
        """
        HTMLレポートを生成する（BaseExecutorとの互換性を保つメソッド）
        
        Args:
            job_id: ジョブID
            job_name: ジョブ名
            image_records: データベースから取得した画像レコードのリスト
            variables: 変数定義のリスト
            output_dir: 出力ディレクトリ
        """
        try:
            # 画像データを変換
            images = self._convert_image_records(image_records, variables)
            
            # レポートデータを作成
            job_data = JobReportData(
                job_id=job_id,
                job_name=job_name,
                images=images,
                variables=variables,
                variable_name=variables[0]['input_name'] if variables else "variable"
            )
            
            # 出力パスを決定
            output_path = Path(output_dir) / f"report_job_{job_id}.html"
            
            # HTMLレポートを生成
            self.html_generator.generate(job_data, output_path)
            
        except Exception as e:
            logger.error(f"Failed to generate report for job {job_id}", exc_info=True)
            raise
    
    def _convert_image_records(self, image_records: List[Dict], variables: List[Dict]) -> List[ImageData]:
        """
        データベースの画像レコードをImageDataに変換
        
        Args:
            image_records: データベースから取得した画像レコードのリスト
            variables: 変数定義のリスト
            
        Returns:
            ImageDataのリスト
        """
        images = []
        
        if not variables:
            logger.warning("No variables provided for image record conversion")
            return images
        
        # 最初の変数を使用（BaseExecutorの既存動作を踏襲、後方互換性）
        first_variable = variables[0]
        
        for record in image_records:
            try:
                variable_value = None
                
                # Phase 2: parametersから全variableの値を抽出（優先）
                if 'parameters' in record and record['parameters']:
                    try:
                        parameters = json.loads(record['parameters'])
                        # 最初のvariableの値を取得（後方互換性）
                        first_var_key = f"{first_variable['node_id']}.{first_variable['input_name']}"
                        variable_value = parameters.get(first_var_key)
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.debug(f"Failed to parse parameters for record {record.get('id')}: {e}")
                
                # parametersから取得できない場合はworkflowから抽出（フォールバック）
                if variable_value is None:
                    workflow = json.loads(record['workflow'])
                    node_id_str = str(first_variable['node_id'])
                    if node_id_str in workflow:
                        variable_value = workflow[node_id_str]['inputs'].get(first_variable['input_name'])
                
                image_data = ImageData(
                    id=record['id'],
                    filepath=record['filepath'],
                    variable_value=variable_value,
                    status=record.get('status', 'success')
                )
                
                images.append(image_data)
                
            except (KeyError, json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Failed to process image record {record.get('id', 'unknown')}: {e}")
                continue
        
        return images