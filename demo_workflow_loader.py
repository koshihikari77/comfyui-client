#!/usr/bin/env python3
"""
WorkflowLoaderのデモンストレーション

ワークフローローダーの機能を実際のワークフローファイルで検証する
"""
import sys
from pathlib import Path
from core.workflow_loader import WorkflowLoader


def main():
    """メインデモ関数"""
    
    # 実際のワークフローファイルを使用
    workflow_path = Path("configs/workflows/api_base.json")
    
    if not workflow_path.exists():
        print(f"Error: Workflow file not found: {workflow_path}")
        print("Please make sure the workflow file exists.")
        return 1
    
    print("🔄 WorkflowLoader Demo")
    print("=" * 50)
    
    try:
        # WorkflowLoaderを初期化
        print(f"📁 Loading workflow: {workflow_path}")
        loader = WorkflowLoader(workflow_path)
        
        # ワークフローを読み込み
        workflow_data = loader.load_workflow()
        print(f"✅ Loaded {len(workflow_data)} nodes")
        print()
        
        # ノード一覧を表示
        print("📋 Available Nodes:")
        print("-" * 30)
        nodes = loader.list_nodes()
        for node_id, node_name, class_type in nodes[:10]:  # 最初の10個だけ表示
            print(f"  {node_id:>3} | {node_name:<25} | {class_type}")
        
        if len(nodes) > 10:
            print(f"  ... and {len(nodes) - 10} more nodes")
        print()
        
        # ノード名マッピングの例
        print("🏷️  Node Name Mapping Examples:")
        print("-" * 35)
        name_mapping = loader.get_node_mapping()
        example_names = list(name_mapping.keys())[:5]
        for name in example_names:
            node_id = name_mapping[name]
            print(f"  '{name}' -> ID '{node_id}'")
        print()
        
        # ノード参照解決のデモ
        print("🔍 Node Reference Resolution Demo:")
        print("-" * 38)
        
        test_references = []
        if example_names:
            test_references.extend(example_names[:2])  # 名前での参照
        
        # IDでの参照も追加
        example_ids = list(workflow_data.keys())[:2]
        test_references.extend(example_ids)
        
        for ref in test_references:
            try:
                resolved_id = loader.resolve_node_reference(ref)
                if ref == resolved_id:
                    print(f"  '{ref}' -> '{resolved_id}' (already ID)")
                else:
                    print(f"  '{ref}' -> '{resolved_id}' (name resolved)")
            except ValueError as e:
                print(f"  '{ref}' -> ERROR: {e}")
        print()
        
        # ノード情報の詳細表示
        if example_names:
            print("📊 Detailed Node Info Example:")
            print("-" * 32)
            example_node = example_names[0]
            try:
                info = loader.get_node_info(example_node)
                print(f"  Node: {info['name']}")
                print(f"  ID: {info['id']}")
                print(f"  Type: {info['class_type']}")
                print(f"  Inputs: {', '.join(info['inputs'][:5])}")
                if len(info['inputs']) > 5:
                    print(f"          ... and {len(info['inputs']) - 5} more")
                print(f"  Meta: {info['meta']}")
            except Exception as e:
                print(f"  Error getting info for '{example_node}': {e}")
            print()
        
        # 参照検証のデモ
        print("✅ Reference Validation Demo:")
        print("-" * 30)
        
        validation_refs = []
        if example_names:
            validation_refs.append(example_names[0])  # 有効な名前
        validation_refs.extend(["8", "999", "非存在ノード"])  # 有効/無効なID/名前
        
        results = loader.validate_references(validation_refs)
        for ref, is_valid in results.items():
            status = "✅ Valid" if is_valid else "❌ Invalid"
            print(f"  '{ref}' -> {status}")
        print()
        
        # 実際の使用例
        print("🛠️  Usage Example:")
        print("-" * 18)
        print("  # 従来の方式（ノードID指定）")
        if example_ids:
            print(f"  params = {{'{example_ids[0]}.input_name': 'value'}}")
        
        print("\n  # 新しい方式（ノード名指定）")
        if example_names:
            print(f"  params = {{'{example_names[0]}.input_name': 'value'}}")
        
        print("\n  # どちらも同じノードを指している！")
        print()
        
        print("🎉 Demo completed successfully!")
        return 0
        
    except Exception as e:
        print(f"❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())