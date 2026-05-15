import abc
import json
import os
import copy
import logging
import re
from pathlib import Path

from ..config import Config
from ..interfaces import IServiceContainer, IDatabaseManager, IAPIClient, IPromptResolver
from ..reporting import Reporter
from ..workflow_loader import WorkflowLoader

logger = logging.getLogger(__name__)


def _sanitize_filename_component(value: str) -> str:
    """ファイル名に使えない文字を安全な区切りに置き換える。"""
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" .")
    return sanitized or "scene"

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
        
        # WorkflowLoaderを初期化
        self.workflow_loader = None
        if self.config.base_workflow_path:
            self.workflow_loader = WorkflowLoader(self.config.base_workflow_path)
        
        self.base_workflow = self._load_base_workflow()

    def _load_base_workflow(self) -> dict:
        if not self.workflow_loader:
            return {} # シーケンスジョブなど、ベースが不要な場合
        
        try:
            return self.workflow_loader.load_workflow()
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load workflow: {e}")
            raise

    def _prepare_workflow(self, params: dict) -> dict:
        """解決済みのパラメータ辞書を受け取り、ワークフローに適用する"""
        workflow_copy = copy.deepcopy(self.base_workflow)
        for key, value in params.items():
            try:
                node_id, input_name = self._resolve_node_parameter(key)
                if node_id not in workflow_copy:
                    logger.warning(f"Node ID '{node_id}' not found in workflow. Skipping parameter '{key}'.")
                    continue
                workflow_copy[node_id]['inputs'][input_name] = value
                logger.debug(f"Applied parameter: {key} -> {node_id}.{input_name} = {value}")
            except ValueError as e:
                logger.warning(f"Failed to resolve parameter '{key}': {e}. Skipping.")
                continue
        return workflow_copy
    
    def _resolve_node_parameter(self, param_key: str) -> tuple[str, str]:
        """
        パラメータキーを解決してノードIDと入力名を取得
        
        Args:
            param_key: パラメータキー（"node_name.input_name" または "node_id.input_name"）
            
        Returns:
            (node_id, input_name)のタプル
            
        Raises:
            ValueError: パラメータキーの解析に失敗した場合
        """
        if '.' not in param_key:
            raise ValueError(f"Invalid parameter key format: '{param_key}'. Expected 'node.input' format.")
        
        parts = param_key.split('.', 1)  # 最初の'.'のみで分割
        node_ref, input_name = parts
        
        # WorkflowLoaderが利用可能な場合はノード名解決を試行
        if self.workflow_loader:
            try:
                node_id = self.workflow_loader.resolve_node_reference(node_ref)
                return node_id, input_name
            except ValueError:
                # ノード名として解決できない場合は、IDとして扱う
                pass
        
        # WorkflowLoaderが利用できないか、名前解決に失敗した場合は元の値を使用
        return node_ref, input_name
    
    def get_workflow_node_info(self, node_reference: str) -> dict:
        """
        ワークフローのノード情報を取得（デバッグ用）
        
        Args:
            node_reference: ノード参照（名前またはID）
            
        Returns:
            ノード情報辞書
        """
        if not self.workflow_loader:
            raise RuntimeError("WorkflowLoader is not available")
        
        return self.workflow_loader.get_node_info(node_reference)
    
    def list_workflow_nodes(self) -> list:
        """
        ワークフローの全ノード一覧を取得
        
        Returns:
            (ノードID, ノード名, class_type)のタプルのリスト
        """
        if not self.workflow_loader:
            return []
        
        return self.workflow_loader.list_nodes()
    
    def validate_parameter_references(self, param_keys: list[str]) -> dict:
        """
        パラメータキーのノード参照を検証
        
        Args:
            param_keys: 検証するパラメータキーのリスト
            
        Returns:
            パラメータキーをキー、有効性を値とする辞書
        """
        if not self.workflow_loader:
            return {key: True for key in param_keys}  # WorkflowLoaderが無い場合は全て有効と見なす
        
        # パラメータキーからノード参照部分を抽出
        node_refs = []
        for key in param_keys:
            if '.' in key:
                node_ref = key.split('.', 1)[0]
                node_refs.append(node_ref)
        
        # ノード参照の検証
        node_results = self.workflow_loader.validate_references(node_refs)
        
        # パラメータキー単位の結果に変換
        results = {}
        for key in param_keys:
            if '.' in key:
                node_ref = key.split('.', 1)[0]
                results[key] = node_results.get(node_ref, False)
            else:
                results[key] = False  # 不正な形式
        
        return results

    def _execute_single_run(
        self,
        job_id: int,
        workflow: dict,
        params: dict,
        scene_id: str | None = None,
    ):
        """1回の画像生成を実行し、結果をDBに保存する"""
        # DBに保存するworkflowは、パラメータ適用後のもの
        # parametersも保存して完全な再現性を確保（設計書要件）
        image_id = self.db.create_image_record(job_id, workflow, params)
        
        try:
            prompt_id = self.api.queue_prompt(workflow)
            self.api.wait_for_completion(prompt_id)
            
            result = self.api.get_generated_image(prompt_id)
            if not result:
                raise RuntimeError("Failed to get generated image from history.")

            _, image_data = result

            safe_scene_id = (
                _sanitize_filename_component(scene_id) if scene_id is not None else None
            )
            filename = (
                f"{safe_scene_id}_{image_id:08d}.png"
                if safe_scene_id
                else f"{image_id:08d}.png"
            )
            image_save_path = self.results_images_dir / filename
            with open(image_save_path, "wb") as f:
                f.write(image_data)

            db_filepath = os.path.join('results', 'images', filename)
            self.db.update_image_record(image_id, db_filepath, 'success')
            self._save_wd14_tags(prompt_id, image_id)
            return True

        except Exception as e:
            self.db.update_image_record(image_id, None, 'failed')
            logger.error(f"Single run failed for image_id {image_id}", exc_info=True)
            return False

    # base.json の ShowText|pysssss ノード ID。WD14Tagger の出力を受ける。
    # 別 workflow を使う場合は config 化する（現状は固定）。
    WD14_SHOWTEXT_NODE_ID = "367"
    WD14_MODEL_NAME = "wd-vit-tagger-v3"

    def _save_wd14_tags(self, prompt_id: str, image_id: int) -> None:
        """ComfyUI history から WD14Tagger 出力を取り、images.tags_json に保存する。
        ノードが存在しない / タグ取得失敗時は warning だけ出して握りつぶす。
        """
        try:
            tags_text = self.api.get_node_text_output(
                prompt_id, self.WD14_SHOWTEXT_NODE_ID
            )
        except Exception:
            logger.warning(
                f"WD14 tags fetch failed for image_id {image_id}", exc_info=True
            )
            return

        if not tags_text:
            return

        tags = [t.strip() for t in tags_text.split(",") if t.strip()]
        try:
            self.db.update_image_tags(image_id, tags, model=self.WD14_MODEL_NAME)
        except Exception:
            logger.warning(
                f"WD14 tags DB write failed for image_id {image_id}", exc_info=True
            )

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
