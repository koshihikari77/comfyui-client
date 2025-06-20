import itertools
import re
import logging
from .base_executor import BaseExecutor

logger = logging.getLogger(__name__)

class GridSearchJobExecutor(BaseExecutor):
    def run(self):
        job_id = self.db.create_job(self.config.job_name, self.config.job_config_data)
        logger.info(f"🚀 Starting GRID SEARCH job: '{self.config.job_name}' (ID: {job_id})")

        try:
            processed_variables = self._preprocess_variables()
            value_lists = [var['values'] for var in processed_variables]
            all_combinations = list(itertools.product(*value_lists))
            total_runs = len(all_combinations)
            logger.info(f"Total combinations to run: {total_runs}")

            for i, current_values in enumerate(all_combinations):
                params = {}
                log_items = []
                for var_def, value in zip(processed_variables, current_values):
                    key = f"{var_def['node_id']}.{var_def['input_name']}"
                    params[key] = self.prompt_resolver.resolve(value) if isinstance(value, str) else value
                    log_items.append(f"{var_def['input_name']}='{str(value)[:30]}...'")
                
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
            if 'text' not in var_def['input_name'].lower():
                processed_vars.append(var_def)
                continue

            # プロンプト変数の場合、valuesをプレースホルダーで展開
            new_values = []
            for template in var_def.get('values', []):
                if isinstance(template, str) and '{' in template and '}' in template:
                    expanded_prompts = self._expand_placeholders(template, placeholders)
                    new_values.extend(expanded_prompts)
                else:
                    new_values.append(template)
            
            # 展開後の新しい変数定義を作成
            new_var_def = var_def.copy()
            new_var_def['values'] = new_values
            processed_vars.append(new_var_def)
            
        return processed_vars

    def _expand_placeholders(self, template: str, placeholders: dict) -> list[str]:
        """
        単一のプロンプトテンプレート文字列とプレースホルダー定義を受け取り、
        全組み合わせの文字列リストを返す。
        例: "A, {B}, {C}" -> ["A, b1, c1", "A, b1, c2", "A, b2, c1", "A, b2, c2"]
        """
        # 1. テンプレートからプレースホルダー名 (例: ['B', 'C']) を抽出
        placeholder_names = re.findall(r'{(.*?)}', template)
        if not placeholder_names:
            return [template] # プレースホルダーがなければそのまま返す

        # 2. 各プレースホルダーの値リストを取得
        try:
            value_lists = [placeholders[name] for name in placeholder_names]
        except KeyError as e:
            raise ValueError(f"Placeholder {{{e.args[0]}}} not found in placeholders definition.")

        # 3. 値の全組み合わせを生成
        # 例: [('b1', 'c1'), ('b1', 'c2'), ('b2', 'c1'), ('b2', 'c2')]
        combinations = list(itertools.product(*value_lists))

        # 4. 各組み合わせを元のテンプレートに埋め込んで最終的な文字列リストを作成
        expanded_strings = []
        for combo in combinations:
            temp_string = template
            for name, value in zip(placeholder_names, combo):
                temp_string = temp_string.replace(f'{{{name}}}', str(value), 1)
            expanded_strings.append(temp_string)
            
        logger.debug(f"Expanded template '{template[:30]}...' into {len(expanded_strings)} prompts.")
        return expanded_strings

    def _generate_report(self, job_id: int):
        # 将来的にグリッド表示に対応させる必要がある
        # 現状はBaseExecutorのものを流用
        logger.warning("Grid search report is not optimized. It will show only the first variable's values.")
        super()._generate_report(job_id)
