import itertools
import logging
from .base_executor import BaseExecutor
from ..interfaces import IServiceContainer
from ..config import Config

logger = logging.getLogger(__name__)

class GridSearchJobExecutor(BaseExecutor):
    def run(self):
        job_id = self.db.create_job(self.config.job_name, self.config.job_config_data)
        logger.info(f"🚀 Starting GRID SEARCH job: '{self.config.job_name}' (ID: {job_id})")

        try:
            processed_variables = self._preprocess_variables()
            # Pydanticモデルなので属性アクセスを使用
            value_lists = [var.values for var in processed_variables]
            all_combinations = list(itertools.product(*value_lists))
            total_runs = len(all_combinations)
            logger.info(f"Total combinations to run: {total_runs}")

            for i, current_values in enumerate(all_combinations):
                params = {}
                log_items = []
                for var_def, value in zip(processed_variables, current_values):
                    # node_idはUnion[int, str]なのでstr()で統一
                    key = f"{var_def.node_id}.{var_def.input_name}"
                    params[key] = self.prompt_resolver.resolve(value) if isinstance(value, str) else value
                    log_items.append(f"{var_def.input_name}='{str(value)[:30]}...'")
                
                logger.info(f"  [{i+1}/{total_runs}] Processing with {', '.join(log_items)}")
                
                workflow = self._prepare_workflow(params)
                self._execute_single_run(job_id, workflow, params)

            self.db.complete_job(job_id)
            self._generate_report(job_id)
        except Exception as e:
            logger.critical(f"Grid search job {job_id} failed critically.", exc_info=True)
        finally:
            self.db.close()

    def _preprocess_variables(self) -> list:
        """
        configの'variables'セクションを処理し、プロンプトテンプレート内の
        プレースホルダーを展開した新しいvariablesリストを返す。
        """
        original_variables = self.config.variables
        placeholders = self.config.placeholders
        if not placeholders:
            return original_variables # プレースホルダーがなければ何もしない

        logger.debug("Preprocessing variables to expand placeholders...")
        
        processed_vars = []
        for var_def in original_variables:
            # プロンプト変数でなければそのままリストに追加
            # (ここでは単純にinput_nameが'text'かどうかで判定)
            # Pydanticモデルなので属性アクセスを使用
            if 'text' not in var_def.input_name.lower():
                processed_vars.append(var_def)
                continue

            # プロンプト変数の場合、valuesをプレースホルダーで展開
            new_values = []
            for template in var_def.values:
                if isinstance(template, str) and '{' in template and '}' in template:
                    expanded_prompts = self.prompt_resolver.expand_placeholders(template, placeholders)
                    new_values.extend(expanded_prompts)
                else:
                    new_values.append(template)
            
            # 展開後の新しい変数定義を作成（Pydanticモデルのコピー）
            from core.schemas.config_models import VariableModel
            new_var_def = VariableModel(
                node_id=var_def.node_id,
                input_name=var_def.input_name,
                values=new_values
            )
            processed_vars.append(new_var_def)
            
        return processed_vars


    def _generate_report(self, job_id: int):
        """GridSearch用のレポート生成（全variable情報を渡す）"""
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
                'parameters': record_dict.get('parameters'),  # Phase 2で追加された列
                'status': record_dict.get('status', 'success')
            })
        
        # Reporterを使用してHTMLレポート生成（全variablesを渡す）
        self.reporter.generate_html_report(
            job_id=job_id,
            job_name=self.config.job_name,
            image_records=image_dicts,
            variables=self.config.variables  # 全variable情報を渡す（Phase 4改善）
        )
