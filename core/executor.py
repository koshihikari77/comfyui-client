import json
import os
import copy
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
        job_id = self.db.create_job(self.config.job_name, self.config.job_data)
        logger.info(f"🚀 Starting job: '{self.config.job_name}' (ID: {job_id})")

        variable = self.config.variable
        values = variable['values']
        
        try:
            for i, value in enumerate(values):
                logger.info(f"  [{i+1}/{len(values)}] Processing with {variable['input_name']} = {value} ...")
                current_workflow = self._prepare_workflow(variable, value)
                self._execute_single_run(job_id, current_workflow)
                logger.info(f"  [{i+1}/{len(values)}] Success!")

            self.db.complete_job(job_id)
            self._generate_report(job_id)

        except Exception as e:
            logger.error(f"An error occurred during job {job_id}", exc_info=True)
        finally:
            self.db.close()

    def _prepare_workflow(self, variable: dict, value) -> dict:
        workflow_copy = copy.deepcopy(self.base_workflow)
        node_id = str(variable['node_id'])
        input_name = variable['input_name']
        
        if node_id not in workflow_copy:
            raise KeyError(f"Node ID '{node_id}' not found in the base workflow.")
        
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
        logger.info(f"📊 Generating report for job {job_id}...")
        env = Environment(loader=FileSystemLoader('templates/'))
        template = env.get_template('report.html.j2')
        image_records = self.db.get_images_by_job_id(job_id)
        variable = self.config.variable
        formatted_images = []
        for record in image_records:
            workflow = json.loads(record['workflow'])
            variable_value = workflow[str(variable['node_id'])]['inputs'][variable['input_name']]
            formatted_images.append({
                'id': record['id'],
                'filepath': record['filepath'],
                'variable_value': variable_value
            })
        html_content = template.render(
            job_name=self.config.job_name,
            job_id=job_id,
            images=formatted_images,
            variable_name=variable['input_name']
        )
        report_path = Path(f"results/report_job_{job_id}.html")
        with open(report_path, "w", encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"✅ Report saved for job {job_id}.")