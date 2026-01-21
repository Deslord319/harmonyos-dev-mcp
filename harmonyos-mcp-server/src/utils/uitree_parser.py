"""
UI组件树解析器
解析hidumper输出的UI组件树文本，转换为结构化的JSON数据
"""
import re
from typing import Dict, List, Any, Optional
from loguru import logger


class UITreeParser:
    """UI组件树解析器"""
    
    def __init__(self):
        """初始化解析器"""
        self.current_depth = 0
        self.node_stack = []
    
    def parse(self, raw_tree: str) -> Dict[str, Any]:
        """
        解析UI组件树文本
        
        Args:
            raw_tree: hidumper输出的原始文本
        
        Returns:
            结构化的UI树JSON数据
        """
        if not raw_tree:
            logger.warning("UI组件树文本为空")
            return {'nodes': [], 'count': 0}
        
        lines = raw_tree.split('\n')
        root_nodes = []
        node_stack = []  # (depth, node) 元组的栈
        
        current_node = None
        current_depth = -1
        
        for line in lines:
            # 检测组件节点行（以 |-> 开头）
            component_match = re.match(r'^(\s*)\|->\s*(\w+)\s+childSize:(\d+)', line)
            if component_match:
                indent = len(component_match.group(1))
                component_type = component_match.group(2)
                child_size = int(component_match.group(3))
                
                # 计算深度（每2个空格为一层）
                depth = indent // 2
                
                # 创建新节点
                new_node = {
                    'type': component_type,
                    'childSize': child_size,
                    'properties': {},
                    'children': []
                }
                
                # 处理节点层级关系
                while node_stack and node_stack[-1][0] >= depth:
                    node_stack.pop()
                
                if node_stack:
                    # 添加到父节点的children
                    parent_node = node_stack[-1][1]
                    parent_node['children'].append(new_node)
                else:
                    # 根节点
                    root_nodes.append(new_node)
                
                # 压入栈
                node_stack.append((depth, new_node))
                current_node = new_node
                current_depth = depth
                
            # 解析属性行（以 | 开头，但不是 |-> ）
            elif current_node is not None:
                prop_match = re.match(r'^\s*\|\s+([^:]+):\s*(.+)$', line)
                if prop_match:
                    prop_name = prop_match.group(1).strip()
                    prop_value = prop_match.group(2).strip()
                    
                    # 特殊处理某些属性
                    if prop_name in ['ID', 'Depth', 'childSize', 'InstanceId', 'AccessibilityId']:
                        try:
                            current_node['properties'][prop_name] = int(prop_value)
                        except ValueError:
                            current_node['properties'][prop_name] = prop_value
                    elif prop_name in ['IsOnMaintree', 'IsVisible', 'StateEffect', 'CreateWithLabel']:
                        current_node['properties'][prop_name] = prop_value.lower() in ['true', '1']
                    else:
                        current_node['properties'][prop_name] = prop_value
        
        # 构建结果
        result = {
            'nodes': root_nodes,
            'count': self._count_nodes(root_nodes)
        }
        
        logger.info(f"解析完成，共 {result['count']} 个节点")
        return result
    
    def _count_nodes(self, nodes: List[Dict]) -> int:
        """递归计算节点总数"""
        count = len(nodes)
        for node in nodes:
            if 'children' in node:
                count += self._count_nodes(node['children'])
        return count
    
    def find_nodes_by_type(self, tree: Dict[str, Any], component_type: str) -> List[Dict[str, Any]]:
        """
        查找指定类型的所有节点
        
        Args:
            tree: UI树数据
            component_type: 组件类型（如 "Button", "Text" 等）
        
        Returns:
            匹配的节点列表
        """
        results = []
        
        def search(nodes):
            for node in nodes:
                if node.get('type') == component_type:
                    results.append(node)
                if 'children' in node:
                    search(node['children'])
        
        search(tree.get('nodes', []))
        return results
    
    def find_node_by_id(self, tree: Dict[str, Any], node_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID查找节点
        
        Args:
            tree: UI树数据
            node_id: 节点ID
        
        Returns:
            匹配的节点，如果未找到则返回None
        """
        def search(nodes):
            for node in nodes:
                if node.get('properties', {}).get('ID') == node_id:
                    return node
                if 'children' in node:
                    result = search(node['children'])
                    if result:
                        return result
            return None
        
        return search(tree.get('nodes', []))

