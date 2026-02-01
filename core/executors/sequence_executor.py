import random
import logging
import re
from typing import Dict, List
from .base_executor import BaseExecutor
from ..interfaces import IServiceContainer
from ..config import Config

logger = logging.getLogger(__name__)

class SequenceJobExecutor(BaseExecutor):
    def __init__(self, config: Config, service_container: IServiceContainer):
        super().__init__(config, service_container)
        self._resolved_iterators: Dict[str, List[str]] = {}
        self._iterator_counters: Dict[str, int] = {}  # 各Iteratorの独立カウンタ
    
    def run(self):
        job_id = self.db.create_job(self.config.job_name, self.config.job_config_data)
        logger.info(f"🚀 Starting SEQUENCE job: '{self.config.job_name}' (ID: {job_id})")
        
        try:
            # Iterator事前処理
            self._resolved_iterators = self._preprocess_iterators()
            # 各Iteratorのカウンタを初期化
            self._iterator_counters = {name: 0 for name in self._resolved_iterators.keys()}
            
            total_runs = sum((p.runs or self.config.default_runs) for p in self.config.prompts)
            run_counter = 0
            
            for prompt_def in self.config.prompts:
                template = prompt_def.template
                # runsがNoneの場合はdefault_runsを使用
                num_runs = prompt_def.runs or self.config.default_runs

                for i in range(num_runs):
                    run_counter += 1
                    
                    # Constant記法の置換処理
                    processed_template = self._substitute_constant_syntax(template)
                    
                    # Iterator記法の置換処理（各Iteratorが独立に巡回）
                    processed_template = self._substitute_iterator_syntax(processed_template)
                    
                    logger.info(f"  [{run_counter}/{total_runs}] Running with template: '{processed_template[:70]}...'")
                    
                    params = self._build_params(processed_template, run_counter - 1, prompt_def)
                    workflow = self._prepare_workflow(params)
                    self._execute_single_run(job_id, workflow, params)

            self.db.complete_job(job_id)
            # self._generate_report(job_id) # シーケンスジョブでは不要かもしれない
        except Exception as e:
            logger.critical(f"Sequence job {job_id} failed critically.", exc_info=True)
        finally:
            self.db.close()

    def _build_params(self, template: str, iteration_index: int, prompt_def) -> dict:
        params = {}
        
        # 1. 固定パラメータを適用（最低優先度）
        if self.config.fixed_parameters:
            for p in self.config.fixed_parameters:
                # Pydanticモデルなので属性アクセスを使用
                key = f"{p.node_id}.{p.input_name}"
                params[key] = p.value

        # 2. ランダムパラメータを生成（中優先度）
        if self.config.random_parameters:
            for p in self.config.random_parameters:
                # Pydanticモデルなので属性アクセスを使用
                key = f"{p.node_id}.{p.input_name}"
                if p.type == 'int':
                    params[key] = random.randint(p.range[0], p.range[1])
                elif p.type == 'choice':
                    params[key] = random.choice(p.values)
        
        # 3. パラメータ組み合わせを適用
        if self.config.parameter_combinations:
            combination = self._get_current_parameter_combination(iteration_index)
            if combination:
                for param in combination.parameters:
                    key = f"{param.node_id}.{param.input_name}"
                    params[key] = param.value

        # 4. scene_delta 由来の params を適用（fixed/random/parameter_combinations より優先）
        if getattr(prompt_def, 'params', None):
            for p in prompt_def.params:
                key = f"{p.node_id}.{p.input_name}"
                params[key] = p.value

        # 5. プロンプトを解決して prompt_target に適用（最後に適用し、常にプロンプトが勝つ）
        resolved_prompt = self.prompt_resolver.resolve(template)
        logger.info(f" resolved prompt (full): '{resolved_prompt}'")
        prompt_target = self.config.job_data.get('prompt_target')
        if prompt_target:
            key = f"{prompt_target['node_id']}.{prompt_target['input_name']}"
            params[key] = resolved_prompt

        return params

    def _preprocess_iterators(self) -> Dict[str, List[str]]:
        """
        Iteratorの事前処理：expand_presetを解決し文字列リストに統一
        
        Returns:
            解決済みIterator辞書 {iterator_name: [resolved_values...]}
        """
        resolved = {}
        
        if not hasattr(self.config, 'iterators') or not self.config.iterators:
            logger.debug("No iterators defined, skipping preprocessing")
            return resolved
        
        for iterator_name, iterator_value in self.config.iterators.items():
            try:
                if isinstance(iterator_value, list):
                    # 手動リスト定義の場合
                    resolved[iterator_name] = iterator_value
                    logger.debug(f"Iterator '{iterator_name}': manual list with {len(iterator_value)} items")
                
                elif isinstance(iterator_value, dict) and 'expand_preset' in iterator_value:
                    # expand_preset指示の場合
                    preset_key = iterator_value['expand_preset']
                    group_names = self.prompt_resolver.get_preset_groups(preset_key)
                    
                    # グループ名から完全なpreset参照形式を生成
                    preset_refs = [f"<preset:{preset_key}#{group}>" for group in group_names]
                    resolved[iterator_name] = preset_refs
                    
                    logger.debug(f"Iterator '{iterator_name}': expanded preset '{preset_key}' into {len(preset_refs)} groups")
                
                else:
                    logger.warning(f"Unknown iterator format for '{iterator_name}': {type(iterator_value)}")
                    resolved[iterator_name] = []
                    
            except Exception as e:
                logger.error(f"Failed to preprocess iterator '{iterator_name}': {e}")
                resolved[iterator_name] = []
        
        logger.info(f"Preprocessed {len(resolved)} iterators")
        return resolved

    def _substitute_constant_syntax(self, template: str) -> str:
        """
        テンプレート内の%constant_name%を実際の値で置換
        
        Args:
            template: 元のテンプレート文字列
            
        Returns:
            置換済みテンプレート文字列
        """
        constants = self.config.constants
        if not constants:
            return template
        
        result = template
        # %constant_name% パターンを検索して置換
        pattern = r'%([a-zA-Z_][a-zA-Z0-9_]*)%'
        
        def replace_constant(match):
            constant_name = match.group(1)
            if constant_name in constants:
                val = constants[constant_name]
                return ", ".join(val) if isinstance(val, list) else val
            else:
                logger.warning(f"Constant '{constant_name}' が見つかりません。そのまま残します。")
                return match.group(0)  # 元の文字列を返す
        
        result = re.sub(pattern, replace_constant, result)
        return result

    def _substitute_iterator_syntax(self, template: str) -> str:
        """
        テンプレート内の$[iterator_name]を実際の値で置換
        
        Args:
            template: 元のテンプレート文字列
            
        Returns:
            置換済みテンプレート文字列
            
        Logic:
            各Iteratorが独立に巡回（各Iteratorごとにカウンタを保持）
        """
        if not self._resolved_iterators:
            return template
        
        # $[iterator_name]パターンを検索・置換
        pattern = r'\$\[([a-zA-Z_][a-zA-Z0-9_]*)\]'
        
        def replace_match(match):
            iterator_name = match.group(1)
            
            if iterator_name not in self._resolved_iterators:
                logger.warning(f"Iterator '{iterator_name}' not found in resolved iterators")
                return match.group(0)  # 元の文字列をそのまま返す
            
            iterator_list = self._resolved_iterators[iterator_name]
            if not iterator_list:
                logger.warning(f"Iterator '{iterator_name}' is empty")
                return match.group(0)
            
            # 各Iteratorが独立に巡回（カウンタを使用）
            current_counter = self._iterator_counters.get(iterator_name, 0)
            selected_index = current_counter % len(iterator_list)
            selected_value = iterator_list[selected_index]
            
            # カウンタをインクリメント（次の呼び出しで次の値を使用）
            self._iterator_counters[iterator_name] = current_counter + 1
            
            logger.debug(f"Iterator '{iterator_name}': counter {current_counter} -> index {selected_index} -> '{selected_value}'")
            return selected_value
        
        result = re.sub(pattern, replace_match, template)
        
        if result != template:
            logger.debug(f"Template substitution: '{template}' -> '{result}'")
        
        return result

    def _get_current_parameter_combination(self, iteration_index: int):
        """
        現在の反復インデックスに対応するパラメータ組み合わせを取得
        
        Args:
            iteration_index: 現在の反復インデックス（0ベース）
            
        Returns:
            ParameterCombinationModel: 選択された組み合わせ、またはNone
        """
        combinations = self.config.parameter_combinations
        if not combinations:
            return None
        
        # 巡回ロジック: index % len(combinations)
        selected_index = iteration_index % len(combinations)
        selected_combination = combinations[selected_index]
        
        logger.debug(f"Parameter combination: index {iteration_index} -> {selected_index} -> '{selected_combination.name}'")
        
        return selected_combination
