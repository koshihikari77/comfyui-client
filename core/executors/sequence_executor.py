import random
import logging
from .base_executor import BaseExecutor
from ..interfaces import IServiceContainer
from ..config import Config

logger = logging.getLogger(__name__)

class SequenceJobExecutor(BaseExecutor):
    def run(self):
        job_id = self.db.create_job(self.config.job_name, self.config.job_config_data)
        logger.info(f"🚀 Starting SEQUENCE job: '{self.config.job_name}' (ID: {job_id})")
        
        try:
            total_runs = sum(p.get('runs', 1) for p in self.config.prompts)
            run_counter = 0
            
            for prompt_def in self.config.prompts:
                template = prompt_def['template']
                num_runs = prompt_def.get('runs', 1)

                for _ in range(num_runs):
                    run_counter += 1
                    logger.info(f"  [{run_counter}/{total_runs}] Running with template: '{template[:70]}...'")
                    
                    params = self._build_params(template)
                    workflow = self._prepare_workflow(params)
                    self._execute_single_run(job_id, workflow, params)

            self.db.complete_job(job_id)
            # self._generate_report(job_id) # シーケンスジョブでは不要かもしれない
        except Exception as e:
            logger.critical(f"Sequence job {job_id} failed critically.", exc_info=True)
        finally:
            self.db.close()

    def _build_params(self, template: str) -> dict:
        params = {}
        # 1. 固定パラメータを適用
        if self.config.fixed_parameters:
            for p in self.config.fixed_parameters:
                key = f"{p['node_id']}.{p['input_name']}"
                params[key] = p['value']

        # 2. ランダムパラメータを生成
        if self.config.random_parameters:
            for p in self.config.random_parameters:
                key = f"{p['node_id']}.{p['input_name']}"
                if p['type'] == 'int':
                    params[key] = random.randint(p['range'][0], p['range'][1])
                elif p['type'] == 'choice':
                    params[key] = random.choice(p['values'])
        
        # 3. プロンプトを解決
        resolved_prompt = self.prompt_resolver.resolve(template)
        logger.info(f" resolved prompt: '{resolved_prompt}...'")
        # ★プロンプトを適用するノードIDと入力名をconfigから取得する必要がある
        #   prompt_target: {node_id: 149, input_name: "text"} のような設定を推奨
        prompt_target = self.config.job_data.get('prompt_target')
        if prompt_target:
             key = f"{prompt_target['node_id']}.{prompt_target['input_name']}"
             params[key] = resolved_prompt
        
        return params
