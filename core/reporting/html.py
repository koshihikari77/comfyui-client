"""
HTML report generator implementation
"""

import os
import logging
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from .base import BaseReportGenerator, JobReportData

logger = logging.getLogger(__name__)


class HTMLReportGenerator(BaseReportGenerator):
    """HTML形式のレポートを生成するクラス"""
    
    def __init__(self, template_dir: str = "templates"):
        """
        HTMLReportGeneratorを初期化
        
        Args:
            template_dir: テンプレートファイルのディレクトリ
        """
        self.template_dir = template_dir
        self.env = Environment(loader=FileSystemLoader(template_dir))
        logger.debug(f"HTMLReportGenerator initialized with template_dir: {template_dir}")
    
    def generate(self, job_data: JobReportData, output_path: Path) -> None:
        """
        HTMLレポートを生成する
        
        Args:
            job_data: ジョブのレポートデータ
            output_path: 出力パス
        """
        logger.info(f"📊 Generating HTML report for job {job_data.job_id}...")
        
        try:
            # テンプレートを取得
            template = self.env.get_template('report.html.j2')
            
            # 画像データを表示用に変換
            formatted_images = self._format_images_for_template(job_data.images)
            
            # HTMLコンテンツを生成
            html_content = template.render(
                job_name=job_data.job_name,
                job_id=job_data.job_id,
                images=formatted_images,
                variable_name=job_data.variable_name
            )
            
            # ファイルに保存
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding='utf-8') as f:
                f.write(html_content)
                
            logger.info(f"✅ HTML report saved to: {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to generate HTML report for job {job_data.job_id}", exc_info=True)
            raise
    
    def _format_images_for_template(self, images: list) -> list:
        """
        画像データをテンプレート用に変換
        
        Args:
            images: ImageDataのリスト
            
        Returns:
            テンプレート用に変換された画像データのリスト
        """
        formatted_images = []
        
        for image in images:
            # results/ からの相対パスに変換
            relative_path = os.path.relpath(image.filepath, 'results').replace('\\', '/')
            
            formatted_images.append({
                'id': image.id,
                'filepath': relative_path,
                'variable_value': image.variable_value
            })
        
        return formatted_images