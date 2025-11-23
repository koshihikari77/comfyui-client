"""
ワークフローローダー

ComfyUIワークフローファイルを読み込み、ノード名による参照を可能にする
"""
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, List

logger = logging.getLogger(__name__)


class WorkflowLoader:
    """ComfyUIワークフローの読み込みとノード名解決を行うクラス"""
    
    def __init__(self, workflow_path: Path):
        """
        ワークフローローダーを初期化
        
        Args:
            workflow_path: ワークフローファイルのパス
        """
        self.workflow_path = workflow_path
        self._workflow_data: Optional[Dict] = None
        self._node_name_mapping: Optional[Dict[str, str]] = None
        self._node_id_mapping: Optional[Dict[str, str]] = None
        
    def load_workflow(self) -> Dict:
        """
        ワークフローファイルを読み込む
        
        Returns:
            ワークフローデータ
            
        Raises:
            FileNotFoundError: ワークフローファイルが見つからない場合
            json.JSONDecodeError: JSONの解析に失敗した場合
        """
        if self._workflow_data is not None:
            return self._workflow_data
            
        if not self.workflow_path.exists():
            raise FileNotFoundError(f"Workflow file not found: {self.workflow_path}")
            
        logger.debug(f"Loading workflow from: {self.workflow_path}")
        
        try:
            with open(self.workflow_path, 'r', encoding='utf-8') as f:
                self._workflow_data = json.load(f)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Failed to parse workflow JSON: {e.msg}", e.doc, e.pos)
            
        # ノードマッピングを作成
        self._build_node_mappings()
        
        logger.info(f"Loaded workflow with {len(self._workflow_data)} nodes")
        return self._workflow_data
    
    def _build_node_mappings(self):
        """ノード名とIDのマッピングを構築"""
        if self._workflow_data is None:
            return
            
        self._node_name_mapping = {}  # name -> id
        self._node_id_mapping = {}    # id -> name
        duplicate_names = []
        
        for node_id, node_data in self._workflow_data.items():
            # _meta.titleからノード名を取得
            node_name = self._extract_node_name(node_id, node_data)
            
            if node_name:
                if node_name in self._node_name_mapping:
                    # 重複する名前を検出
                    duplicate_names.append(node_name)
                    logger.warning(f"Duplicate node name '{node_name}' found: IDs {self._node_name_mapping[node_name]} and {node_id}")
                else:
                    self._node_name_mapping[node_name] = node_id
                    self._node_id_mapping[node_id] = node_name
        
        if duplicate_names:
            logger.warning(f"Found {len(duplicate_names)} duplicate node names: {duplicate_names}")
            
        logger.debug(f"Built node mappings: {len(self._node_name_mapping)} unique names")
    
    def _extract_node_name(self, node_id: str, node_data: Dict) -> Optional[str]:
        """
        ノードデータから名前を抽出
        
        Args:
            node_id: ノードID
            node_data: ノードデータ
            
        Returns:
            ノード名（取得できない場合はNone）
        """
        try:
            # _meta.titleを優先
            if '_meta' in node_data and 'title' in node_data['_meta']:
                title = node_data['_meta']['title'].strip()
                if title:
                    return title
            
            # class_typeをフォールバックとして使用
            if 'class_type' in node_data:
                class_type = node_data['class_type'].strip()
                if class_type:
                    logger.debug(f"Using class_type '{class_type}' as name for node {node_id}")
                    return class_type
                    
        except (KeyError, AttributeError, TypeError) as e:
            logger.debug(f"Failed to extract name for node {node_id}: {e}")
            
        logger.debug(f"No name found for node {node_id}")
        return None
    
    def get_node_mapping(self) -> Dict[str, str]:
        """
        ノード名→IDのマッピングを取得
        
        Returns:
            ノード名をキー、ノードIDを値とする辞書
        """
        if self._workflow_data is None:
            self.load_workflow()
        return self._node_name_mapping.copy()
    
    def get_node_id_mapping(self) -> Dict[str, str]:
        """
        ノードID→名前のマッピングを取得
        
        Returns:
            ノードIDをキー、ノード名を値とする辞書
        """
        if self._workflow_data is None:
            self.load_workflow()
        return self._node_id_mapping.copy()
    
    def resolve_node_reference(self, reference: str) -> str:
        """
        ノード参照を解決（名前→ID変換）
        
        Args:
            reference: ノード参照（名前またはID）
            
        Returns:
            ノードID
            
        Raises:
            ValueError: ノードが見つからない場合
        """
        if self._workflow_data is None:
            self.load_workflow()
            
        # 既にIDの場合はそのまま返す
        if reference in self._workflow_data:
            return reference
            
        # 名前からIDを検索
        if reference in self._node_name_mapping:
            node_id = self._node_name_mapping[reference]
            logger.debug(f"Resolved node name '{reference}' to ID '{node_id}'")
            return node_id
            
        # どちらでも見つからない場合
        available_names = list(self._node_name_mapping.keys())
        available_ids = list(self._workflow_data.keys())
        
        raise ValueError(
            f"Node '{reference}' not found. "
            f"Available names: {available_names[:5]}{'...' if len(available_names) > 5 else ''}, "
            f"Available IDs: {available_ids[:5]}{'...' if len(available_ids) > 5 else ''}"
        )
    
    def get_node_info(self, node_reference: str) -> Dict:
        """
        ノード情報を取得（デバッグ用）
        
        Args:
            node_reference: ノード参照（名前またはID）
            
        Returns:
            ノード情報
        """
        if self._workflow_data is None:
            self.load_workflow()
            
        node_id = self.resolve_node_reference(node_reference)
        node_data = self._workflow_data[node_id]
        
        return {
            'id': node_id,
            'name': self._node_id_mapping.get(node_id, 'Unknown'),
            'class_type': node_data.get('class_type', 'Unknown'),
            'inputs': list(node_data.get('inputs', {}).keys()),
            'meta': node_data.get('_meta', {})
        }
    
    def list_nodes(self) -> List[Tuple[str, str, str]]:
        """
        全ノードの一覧を取得
        
        Returns:
            (ノードID, ノード名, class_type)のタプルのリスト
        """
        if self._workflow_data is None:
            self.load_workflow()
            
        nodes = []
        for node_id, node_data in self._workflow_data.items():
            node_name = self._node_id_mapping.get(node_id, 'Unknown')
            class_type = node_data.get('class_type', 'Unknown')
            nodes.append((node_id, node_name, class_type))
            
        return sorted(nodes, key=lambda x: int(x[0]) if x[0].isdigit() else x[0])
    
    def validate_references(self, references: List[str]) -> Dict[str, bool]:
        """
        ノード参照のリストを検証
        
        Args:
            references: 検証するノード参照のリスト
            
        Returns:
            参照をキー、有効性を値とする辞書
        """
        if self._workflow_data is None:
            self.load_workflow()
            
        results = {}
        for ref in references:
            try:
                self.resolve_node_reference(ref)
                results[ref] = True
            except ValueError:
                results[ref] = False
                
        return results