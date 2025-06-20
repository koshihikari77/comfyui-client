import abc
import json
import os
import copy
import logging
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from ..config import Config
from ..interfaces import IServiceContainer, IDatabaseManager, IAPIClient, IPromptResolver

logger = logging.getLogger(__name__)

class BaseExecutor(abc.ABC):
    def __init__(self, config: Config, service_container: IServiceContainer):
        self.config = config
        self.service_container = service_container
        self.db = service_container.get_database_manager()
        self.api = service_container.get_api_client()
        self.prompt_resolver = service_container.get_prompt_resolver()
        self.results_images_dir = Path("results/images")
        self.results_images_dir.mkdir(parents=True, exist_ok=True)
        self.base_workflow = self._load_base_workflow()

    def _load_base_workflow(self) -> dict:
        path = self.config.base_workflow_path
        if not path:
            return {} # シーケンスジョブなど、ベースが不要な場合
        if not path.exists():
            raise FileNotFoundError(f"Base workflow not found: {path}")
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _prepare_workflow(self, params: dict) -> dict:
        """解決済みのパラメータ辞書を受け取り、ワークフローに適用する"""
        workflow_copy = copy.deepcopy(self.base_workflow)
        for key, value in params.items():
            node_id, input_name = key.split('.')
            if node_id not in workflow_copy:
                logger.warning(f"Node ID '{node_id}' not found in workflow. Skipping.")
                continue
            workflow_copy[node_id]['inputs'][input_name] = value
        return workflow_copy

    def _execute_single_run(self, job_id: int, workflow: dict, params: dict):
        """1回の画像生成を実行し、結果をDBに保存する"""
        # DBに保存するworkflowは、パラメータ適用後のもの
        image_id = self.db.create_image_record(job_id, workflow)
        
        try:
            prompt_id = self.api.queue_prompt(workflow)
            self.api.wait_for_completion(prompt_id)
            
            result = self.api.get_generated_image(prompt_id)
            if not result:
                raise RuntimeError("Failed to get generated image from history.")

            _, image_data = result
            
            image_save_path = self.results_images_dir / f"{image_id:08d}.png"
            with open(image_save_path, "wb") as f:
                f.write(image_data)
                
            db_filepath = os.path.join('results', 'images', f"{image_id:08d}.png")
            self.db.update_image_record(image_id, db_filepath, 'success')
            return True

        except Exception as e:
            self.db.update_image_record(image_id, None, 'failed')
            logger.error(f"Single run failed for image_id {image_id}", exc_info=True)
            return False

    @abc.abstractmethod
    def run(self):
        """ジョブを実行するメインロジック。サブクラスで実装する"""
        pass

    def _generate_report(self, job_id: int):
        # レポート生成も将来的にグリッド表示に対応させる必要があるが、
        # 今は単一変数の時と同じ表示方法で代用する
        logger.info(f"📊 Generating report for job {job_id}...")
        env = Environment(loader=FileSystemLoader('templates/'))
        template = env.get_template('report.html.j2')

        image_records = self.db.get_images_by_job_id(job_id)
        
        # ひとまず最初の変数だけをレポートに表示する
        first_variable = self.config.variables[0]
        formatted_images = []
        for record in image_records:
            workflow = json.loads(record['workflow'])
            # ワークフローから全ての変数値を取得して表示するのが理想だが、まずはシンプルに
            variable_value = workflow[str(first_variable['node_id'])]['inputs'][first_variable['input_name']]
            formatted_images.append({
                'id': record['id'],
                'filepath': os.path.relpath(record['filepath'], 'results').replace('\\', '/'),
                'variable_value': variable_value
            })

        html_content = template.render(
            job_name=self.config.job_name,
            job_id=job_id,
            images=formatted_images,
            variable_name=first_variable['input_name']
        )
        
        report_path = Path("results") / f"report_job_{job_id}.html"
        with open(report_path, "w", encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"✅ Report saved to: {report_path}")