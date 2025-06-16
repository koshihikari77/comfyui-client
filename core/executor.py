import json
import os
import copy
import itertools
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import logging

from .config import Config
from .database import DatabaseManager
from .api_client import ComfyUI_APIClient

logger = logging.getLogger(__name__)

class JobExecutor:
    def __init__(self, config: Config):
        self.config = config
        logger.debug("Initializing DatabaseManager...")
        self.db = DatabaseManager()
        logger.debug("Initializing ComfyUI_APIClient...")
        self.api = ComfyUI_APIClient(self.config.server_address)
        self.results_images_dir = Path("results/images")
        self.results_images_dir.mkdir(parents=True, exist_ok=True)
        self.base_workflow = self._load_base_workflow()
        logger.debug("JobExecutor initialized.")

    def _load_base_workflow(self) -> dict:
        if not self.config.base_workflow_path.exists():
            raise FileNotFoundError(f"Base workflow not found: {self.config.base_workflow_path}")
        with open(self.config.base_workflow_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def run(self):
        job_id = self.db.create_job(self.config.job_name, self.config.job_config_data)
        logger.info(f"🚀 Starting job: '{self.config.job_name}' (ID: {job_id})")

        try:
            
            # 1. 変数定義と値のリストを準備
            variables = self.config.variables
            value_lists = [var['values'] for var in variables]

            # 2. 全ての組み合わせ（デカルト積）を生成
            # 例: [[0.5, 0.6], [1001, 1002]] -> (0.5, 1001), (0.5, 1002), (0.6, 1001), (0.6, 1002)
            all_combinations = list(itertools.product(*value_lists))
            total_runs = len(all_combinations)
            logger.info(f"Total combinations to run: {total_runs}")

            # 3. 各組み合わせでループ実行
            for i, current_values in enumerate(all_combinations):
                
                # どの値で実行しているかログに出力
                log_message = ", ".join(
                    f"{variables[j]['input_name']}={current_values[j]}" for j in range(len(variables))
                )
                logger.info(f"  [{i+1}/{total_runs}] Processing with {log_message} ...")

                # 4. 現在の組み合わせでワークフローを準備
                current_workflow = self._prepare_workflow(variables, current_values)
                
                # 5. 画像生成を実行
                self._execute_single_run(job_id, current_workflow)
                logger.info(f"  [{i+1}/{total_runs}] Success!")

            self.db.complete_job(job_id)
            self._generate_report(job_id)

        except Exception as e:
            logger.error(f"An error occurred during job {job_id}", exc_info=True)
        finally:
            self.db.close()

    def _prepare_workflow(self, variables: list, current_values: tuple) -> dict:
        """複数の変数とfixed_parametersを適用してワークフローを準備する"""
        workflow_copy = copy.deepcopy(self.base_workflow)

        # 1. 固定パラメータを先に適用
        if 'fixed_parameters' in self.config.job_config_data:
            for param in self.config.job_config_data['fixed_parameters']:
                node_id = str(param['node_id'])
                input_name = param['input_name']
                fixed_value = param['value']
                if node_id not in workflow_copy:
                    logger.warning(f"Node ID '{node_id}' for fixed_parameter not found.")
                    continue
                logger.debug(f"Applying fixed param: Node {node_id}, Input '{input_name}' = '{fixed_value}'")
                workflow_copy[node_id]['inputs'][input_name] = fixed_value

        # 2. 変数リストを適用
        for var_def, value in zip(variables, current_values):
            node_id = str(var_def['node_id'])
            input_name = var_def['input_name']
            if node_id not in workflow_copy:
                raise KeyError(f"Node ID '{node_id}' not found in the base workflow.")
            logger.debug(f"Applying: Node {node_id}, Input '{input_name}' = {value}")
            workflow_copy[node_id]['inputs'][input_name] = value

        return workflow_copy

    def _execute_single_run(self, job_id: int, workflow: dict):
        logger.debug(f"Executing single run for job {job_id}...")
        image_id = self.db.create_image_record(job_id, workflow)
        
        try:
            prompt_id = self.api.queue_prompt(workflow)
            self.api.wait_for_completion(prompt_id)
            result = self.api.get_generated_image(prompt_id)
            if not result:
                raise RuntimeError("Failed to get generated image from history.")
            _, image_data = result
            image_path = self.results_images_dir / f"{image_id:08d}.png"
            with open(image_path, "wb") as f:
                f.write(image_data)
            self.db.update_image_record(image_id, str(self.results_images_dir / f"{image_id:08d}.png"), 'success')
        except Exception as e:
            self.db.update_image_record(image_id, None, 'failed')
            raise e # Propagate error to the main run loop

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