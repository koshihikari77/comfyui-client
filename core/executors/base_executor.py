import abc
import json
import os
import copy
import logging
from pathlib import Path

from ..config import Config
from ..interfaces import IServiceContainer, IDatabaseManager, IAPIClient, IPromptResolver
from ..reporting import Reporter

logger = logging.getLogger(__name__)

class BaseExecutor(abc.ABC):
    def __init__(self, config: Config, service_container: IServiceContainer):
        self.config = config
        self.service_container = service_container
        self.db = service_container.get_database_manager()
        self.api = service_container.get_api_client()
        self.prompt_resolver = service_container.get_prompt_resolver()
        self.reporter = Reporter()
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
        """新しいReportingモジュールを使用してレポート生成"""
        image_records = self.db.get_images_by_job_id(job_id)
        
        # データベースレコードを辞書形式に変換（sqlite3.Rowから）
        image_dicts = []
        for record in image_records:
            # sqlite3.Rowオブジェクトを辞書に変換
            record_dict = dict(record)
            image_dicts.append({
                'id': record_dict['id'],
                'filepath': record_dict['filepath'],
                'workflow': record_dict['workflow'],
                'status': record_dict.get('status', 'success')
            })
        
        # Reporterを使用してHTMLレポート生成
        self.reporter.generate_html_report(
            job_id=job_id,
            job_name=self.config.job_name,
            image_records=image_dicts,
            variables=self.config.variables
        )