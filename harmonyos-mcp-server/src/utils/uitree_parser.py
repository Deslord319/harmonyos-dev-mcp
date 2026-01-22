"""
UI组件树解析器
解析hidumper -inspector 输出的UI组件树文本，转换为结构化的JSON数据
坐标为屏幕绝对坐标，可直接用于 uitest uiInput click 操作
"""
import re
from typing import Dict, List, Any, Optional
from loguru import logger


class UITreeParser:
    """UI组件树解析器（解析 -inspector 格式）"""

    def __init__(self):
        """初始化解析器"""
        self.window_info = {}

    def parse(self, raw_tree: str) -> Dict[str, Any]:
        """
        解析 hidumper -inspector 输出的UI组件树文本

        Args:
            raw_tree: hidumper -inspector 输出的原始文本

        Returns:
            结构化的UI树JSON数据，坐标为屏幕绝对坐标
        """
        if not raw_tree:
            logger.warning("UI组件树文本为空")
            return {'nodes': [], 'count': 0, 'window_info': {}}

        lines = raw_tree.split('\n')
        root_nodes = []
        node_stack = []  # (indent, node) 元组的栈

        current_node = None
        self.window_info = {}

        for line in lines:
            # 解析窗口信息（WindowRect 等）
            window_rect_match = re.match(r'^WindowRect:\s*\[\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\s*\]', line)
            if window_rect_match:
                self.window_info['window_rect'] = {
                    'left': int(window_rect_match.group(1)),
                    'top': int(window_rect_match.group(2)),
                    'width': int(window_rect_match.group(3)),
                    'height': int(window_rect_match.group(4))
                }
                continue

            # 解析其他窗口属性
            for prop in ['WindowName', 'DisplayId', 'WinId', 'Pid', 'bundleName']:
                prop_match = re.match(rf'^{prop}:\s*(.+)$', line)
                if prop_match:
                    self.window_info[prop.lower()] = prop_match.group(1).strip()
                    break

            # 检测组件节点行（以 |-> 开头，例如：|-> root childSize:1）
            component_match = re.match(r'^(\s*)\|->\s*(\w+)\s+childSize:(\d+)', line)
            if component_match:
                indent = len(component_match.group(1))
                component_type = component_match.group(2)
                child_size = int(component_match.group(3))

                # 创建新节点
                new_node = {
                    'type': component_type,
                    'childSize': child_size,
                    'properties': {},
                    'children': []
                }

                # 处理节点层级关系
                while node_stack and node_stack[-1][0] >= indent:
                    node_stack.pop()

                if node_stack:
                    parent_node = node_stack[-1][1]
                    parent_node['children'].append(new_node)
                else:
                    root_nodes.append(new_node)

                node_stack.append((indent, new_node))
                current_node = new_node
                continue

            # 解析属性行（-inspector 格式：| key: value 或 key: value）
            if current_node is not None:
                # 格式1: | key: value
                prop_match = re.match(r'^\s*\|\s*([^:]+):\s*(.*)$', line)
                # 格式2: key: value (缩进的)
                if not prop_match:
                    prop_match = re.match(r'^\s+([^:|]+):\s*(.*)$', line)

                if prop_match:
                    prop_name = prop_match.group(1).strip()
                    prop_value = prop_match.group(2).strip()

                    # 跳过空属性名
                    if not prop_name:
                        continue

                    # 数值属性转换
                    if prop_name in ['ID', 'top', 'left', 'width', 'height']:
                        try:
                            # 处理浮点数（如 505.000000）
                            current_node['properties'][prop_name] = float(prop_value)
                        except ValueError:
                            current_node['properties'][prop_name] = prop_value
                    # 布尔属性
                    elif prop_name in ['visible', 'clickable', 'longclickable', 'checkable',
                                       'scrollable', 'checked']:
                        current_node['properties'][prop_name] = prop_value in ['1', 'true']
                    else:
                        current_node['properties'][prop_name] = prop_value

        result = {
            'nodes': root_nodes,
            'count': self._count_nodes(root_nodes),
            'window_info': self.window_info
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
        """查找指定类型的所有节点"""
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
        """根据ID查找节点"""
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

