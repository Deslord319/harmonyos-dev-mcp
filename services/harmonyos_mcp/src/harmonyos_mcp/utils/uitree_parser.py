"""
UI组件树解析器
支持两种格式:
1. hidumper -inspector 输出的文本格式
2. uitest dumpLayout 输出的JSON格式
坐标为屏幕绝对坐标，可直接用于 uitest uiInput click 操作
"""
import re
import json
import sys
from typing import Dict, List, Any, Optional
from loguru import logger


class UITreeParser:
    """UI组件树解析器"""

    def __init__(self):
        """初始化解析器"""
        self.window_info = {}

    def parse(self, raw_tree: str) -> Dict[str, Any]:
        """
        解析UI组件树（自动检测格式）

        Args:
            raw_tree: UI树原始数据（JSON或文本格式）

        Returns:
            结构化的UI树JSON数据，坐标为屏幕绝对坐标
        """
        if not raw_tree:
            logger.warning("UI组件树文本为空")
            return {'nodes': [], 'count': 0, 'window_info': {}}

        # 临时提高递归限制以处理深层嵌套的 UI 树
        old_limit = sys.getrecursionlimit()
        sys.setrecursionlimit(max(old_limit, 10000))
        
        try:
            # 尝试解析为JSON（uitest dumpLayout格式）
            raw_tree_stripped = raw_tree.strip()
            if raw_tree_stripped.startswith('{'):
                try:
                    json_data = json.loads(raw_tree_stripped)
                    return self._parse_uitest_json(json_data)
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON解析失败，尝试文本解析: {e}")

            # 回退到文本解析（hidumper -inspector格式）
            return self._parse_inspector_text(raw_tree)
        finally:
            # 恢复原来的递归限制
            sys.setrecursionlimit(old_limit)

    def _parse_uitest_json(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析 uitest dumpLayout JSON 格式

        Args:
            json_data: uitest dumpLayout 输出的JSON对象

        Returns:
            标准化的UI树结构
        """
        logger.info("解析 uitest dumpLayout JSON 格式")
        
        def convert_node(node: Dict[str, Any]) -> Dict[str, Any]:
            """转换节点格式"""
            attrs = node.get('attributes', {})
            
            # 解析 bounds: "[868,288][2464,1755]" -> left, top, width, height
            bounds_str = attrs.get('bounds', '')
            left, top, width, height = 0, 0, 0, 0
            bounds_match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)
            if bounds_match:
                x1, y1, x2, y2 = map(int, bounds_match.groups())
                left, top = x1, y1
                width, height = x2 - x1, y2 - y1

            converted = {
                'type': attrs.get('type', ''),
                'properties': {
                    'text': attrs.get('text', ''),
                    'ID': attrs.get('accessibilityId', ''),
                    'compid': attrs.get('hashcode', ''),
                    'left': left,
                    'top': top,
                    'width': width,
                    'height': height,
                    'visible': attrs.get('visible', 'true') == 'true',
                    'clickable': attrs.get('clickable', 'false') == 'true',
                    'enabled': attrs.get('enabled', 'true') == 'true',
                    'focused': attrs.get('focused', 'false') == 'true',
                    'scrollable': attrs.get('scrollable', 'false') == 'true',
                    'checked': attrs.get('checked', 'false') == 'true',
                    'description': attrs.get('description', ''),
                    'bundleName': attrs.get('bundleName', ''),
                    'pagePath': attrs.get('pagePath', ''),
                },
                'children': []
            }

            # 递归转换子节点
            for child in node.get('children', []):
                converted['children'].append(convert_node(child))

            return converted

        # 转换根节点及其子节点
        root_nodes = []
        if 'children' in json_data:
            for child in json_data['children']:
                root_nodes.append(convert_node(child))
        elif 'attributes' in json_data:
            # 单个根节点
            root_nodes.append(convert_node(json_data))

        result = {
            'nodes': root_nodes,
            'count': self._count_nodes(root_nodes),
            'window_info': {},
            'format': 'uitest_json'
        }

        logger.info(f"解析完成，共 {result['count']} 个节点")
        return result

    def _parse_inspector_text(self, raw_tree: str) -> Dict[str, Any]:
        """
        解析 hidumper -inspector 文本格式（原有逻辑）
        """
        logger.info("解析 hidumper -inspector 文本格式")
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
            'window_info': self.window_info,
            'format': 'inspector_text'
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

