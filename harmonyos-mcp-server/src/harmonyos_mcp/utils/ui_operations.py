"""
UI操作工具封装
封装 hdc shell uitest uiInput 命令，提供UI自动化操作能力
"""
import re
from typing import Dict, Any, Optional, List, Tuple
from loguru import logger

from .hdc_wrapper import HdcWrapper


class UIOperations:
    """UI操作工具类"""
    
    def __init__(self, hdc: HdcWrapper):
        """
        初始化UI操作工具
        
        Args:
            hdc: HdcWrapper实例
        """
        self.hdc = hdc
        logger.info("UI操作工具初始化成功")
    
    def _execute_uitest(self, device_id: str, command: str, timeout: int = None) -> Dict[str, Any]:
        """
        执行uitest命令
        
        Args:
            device_id: 设备ID
            command: uitest命令（不包含 uitest uiInput 前缀）
            timeout: 超时时间(秒)，默认使用 UI_OPERATION_TIMEOUT
        
        Returns:
            执行结果
        """
        from harmonyos_mcp.config import Config
        timeout = timeout or Config.UI_OPERATION_TIMEOUT
        full_command = f"uitest uiInput {command}"
        logger.debug(f"执行UI命令: {full_command}, 超时: {timeout}s")
        result = self.hdc.execute_shell(device_id, full_command, timeout=timeout)
        return result
    
    # ========================================================================
    # 点击操作
    # ========================================================================
    
    def click(self, device_id: str, x: int, y: int) -> Dict[str, Any]:
        """
        点击指定坐标
        
        Args:
            device_id: 设备ID
            x: X坐标
            y: Y坐标
        
        Returns:
            操作结果
        """
        logger.info(f"点击坐标: ({x}, {y})")
        result = self._execute_uitest(device_id, f"click {x} {y}")
        return {
            'success': result['success'],
            'action': 'click',
            'x': x,
            'y': y,
            'message': '点击成功' if result['success'] else f'点击失败: {result.get("stderr", "")}'
        }
    
    def double_click(self, device_id: str, x: int, y: int) -> Dict[str, Any]:
        """
        双击指定坐标
        
        Args:
            device_id: 设备ID
            x: X坐标
            y: Y坐标
        
        Returns:
            操作结果
        """
        logger.info(f"双击坐标: ({x}, {y})")
        result = self._execute_uitest(device_id, f"doubleClick {x} {y}")
        return {
            'success': result['success'],
            'action': 'doubleClick',
            'x': x,
            'y': y,
            'message': '双击成功' if result['success'] else f'双击失败: {result.get("stderr", "")}'
        }
    
    def long_click(self, device_id: str, x: int, y: int) -> Dict[str, Any]:
        """
        长按指定坐标
        
        Args:
            device_id: 设备ID
            x: X坐标
            y: Y坐标
        
        Returns:
            操作结果
        """
        logger.info(f"长按坐标: ({x}, {y})")
        result = self._execute_uitest(device_id, f"longClick {x} {y}")
        return {
            'success': result['success'],
            'action': 'longClick',
            'x': x,
            'y': y,
            'message': '长按成功' if result['success'] else f'长按失败: {result.get("stderr", "")}'
        }
    
    # ========================================================================
    # 滑动操作
    # ========================================================================
    
    def swipe(self, device_id: str, from_x: int, from_y: int, 
              to_x: int, to_y: int, speed: int = 600) -> Dict[str, Any]:
        """
        滑动操作（慢滑）
        
        Args:
            device_id: 设备ID
            from_x: 起点X坐标
            from_y: 起点Y坐标
            to_x: 终点X坐标
            to_y: 终点Y坐标
            speed: 滑动速度 (200-40000, 默认600)
        
        Returns:
            操作结果
        """
        # 确保速度在有效范围内
        speed = max(200, min(40000, speed))
        
        logger.info(f"滑动: ({from_x}, {from_y}) -> ({to_x}, {to_y}), 速度: {speed}")
        result = self._execute_uitest(device_id, f"swipe {from_x} {from_y} {to_x} {to_y} {speed}")
        return {
            'success': result['success'],
            'action': 'swipe',
            'from_x': from_x,
            'from_y': from_y,
            'to_x': to_x,
            'to_y': to_y,
            'direction': None,
            'speed': speed,
            'message': '滑动成功' if result['success'] else f'滑动失败: {result.get("stderr", "")}'
        }
    
    def fling(self, device_id: str, from_x: int, from_y: int,
              to_x: int, to_y: int, speed: int = 600, step_length: int = None) -> Dict[str, Any]:
        """
        快滑操作
        
        Args:
            device_id: 设备ID
            from_x: 起点X坐标
            from_y: 起点Y坐标
            to_x: 终点X坐标
            to_y: 终点Y坐标
            speed: 滑动速度 (200-40000, 默认600)
            step_length: 步长（可选，默认为滑动距离/50）
        
        Returns:
            操作结果
        """
        speed = max(200, min(40000, speed))
        
        cmd = f"fling {from_x} {from_y} {to_x} {to_y} {speed}"
        if step_length:
            cmd += f" {step_length}"
        
        logger.info(f"快滑: ({from_x}, {from_y}) -> ({to_x}, {to_y})")
        result = self._execute_uitest(device_id, cmd)
        return {
            'success': result['success'],
            'action': 'fling',
            'from': {'x': from_x, 'y': from_y},
            'to': {'x': to_x, 'y': to_y},
            'message': '快滑成功' if result['success'] else f'快滑失败: {result.get("stderr", "")}'
        }

    def swipe_direction(self, device_id: str, direction: str,
                        speed: int = 600, step_length: int = None) -> Dict[str, Any]:
        """
        按方向滑动

        Args:
            device_id: 设备ID
            direction: 滑动方向 (left/right/up/down)
            speed: 滑动速度 (200-40000, 默认600)
            step_length: 步长（可选）

        Returns:
            操作结果
        """
        # 方向映射: 0=左, 1=右, 2=上, 3=下
        direction_map = {
            'left': 0,
            'right': 1,
            'up': 2,
            'down': 3
        }

        dir_code = direction_map.get(direction.lower())
        if dir_code is None:
            return {
                'success': False,
                'action': 'swipe_direction',
                'message': f'无效的方向: {direction}，支持: left/right/up/down'
            }

        speed = max(200, min(40000, speed))

        cmd = f"dircFling {dir_code} {speed}"
        if step_length:
            cmd += f" {step_length}"

        logger.info(f"方向滑动: {direction}, 速度: {speed}")
        result = self._execute_uitest(device_id, cmd)
        return {
            'success': result['success'],
            'action': 'swipe_direction',
            'direction': direction,
            'from_x': 0,
            'from_y': 0,
            'to_x': 0,
            'to_y': 0,
            'speed': speed,
            'message': f'{direction}滑动成功' if result['success'] else f'滑动失败: {result.get("stderr", "")}'
        }

    # ========================================================================
    # 文本输入
    # ========================================================================

    def input_text(self, device_id: str, x: int, y: int, text: str) -> Dict[str, Any]:
        """
        在指定坐标的输入框中输入文本

        Args:
            device_id: 设备ID
            x: 输入框X坐标
            y: 输入框Y坐标
            text: 要输入的文本

        Returns:
            操作结果
        """
        logger.info(f"输入文本: '{text}' at ({x}, {y})")
        # 使用单引号包裹文本
        result = self._execute_uitest(device_id, f"inputText {x} {y} '{text}'")
        return {
            'success': result['success'],
            'action': 'inputText',
            'x': x,
            'y': y,
            'text': text,
            'message': '文本输入成功' if result['success'] else f'文本输入失败: {result.get("stderr", "")}'
        }

    # ========================================================================
    # 按键操作
    # ========================================================================

    def press_key(self, device_id: str, key: str, key2: str = None) -> Dict[str, Any]:
        """
        模拟按键操作

        Args:
            device_id: 设备ID
            key: 按键名称或ID (Home/Back/Enter等)
            key2: 第二个按键（用于组合键）

        Returns:
            操作结果
        """
        cmd = f"keyEvent {key}"
        if key2:
            cmd += f" {key2}"

        logger.info(f"按键: {key}" + (f" + {key2}" if key2 else ""))
        result = self._execute_uitest(device_id, cmd)
        return {
            'success': result['success'],
            'action': 'keyEvent',
            'key': key,
            'key2': key2,
            'message': '按键成功' if result['success'] else f'按键失败: {result.get("stderr", "")}'
        }

    def press_home(self, device_id: str) -> Dict[str, Any]:
        """返回主页"""
        return self.press_key(device_id, "Home")

    def press_back(self, device_id: str) -> Dict[str, Any]:
        """返回上一步"""
        return self.press_key(device_id, "Back")

    # ========================================================================
    # 拖拽操作
    # ========================================================================

    def drag(self, device_id: str, from_x: int, from_y: int,
             to_x: int, to_y: int, speed: int = 600) -> Dict[str, Any]:
        """
        拖拽操作

        Args:
            device_id: 设备ID
            from_x: 起点X坐标
            from_y: 起点Y坐标
            to_x: 终点X坐标
            to_y: 终点Y坐标
            speed: 拖拽速度 (200-40000, 默认600)

        Returns:
            操作结果
        """
        speed = max(200, min(40000, speed))

        logger.info(f"拖拽: ({from_x}, {from_y}) -> ({to_x}, {to_y})")
        result = self._execute_uitest(device_id, f"drag {from_x} {from_y} {to_x} {to_y} {speed}")
        return {
            'success': result['success'],
            'action': 'drag',
            'from': {'x': from_x, 'y': from_y},
            'to': {'x': to_x, 'y': to_y},
            'speed': speed,
            'message': '拖拽成功' if result['success'] else f'拖拽失败: {result.get("stderr", "")}'
        }

    # ========================================================================
    # 坐标计算辅助方法
    # ========================================================================

    @staticmethod
    def parse_bounds(bounds_str: str) -> Optional[Tuple[int, int, int, int]]:
        """
        解析bounds字符串

        Args:
            bounds_str: bounds字符串，支持多种格式:
                - "[left,top][right,bottom]" (Android 风格)
                - "RectT (x, y) - [width x height]" (HarmonyOS FrameRect 格式)
                - "[x y width height]" (HarmonyOS Bounds 格式)

        Returns:
            (left, top, width, height) 元组，解析失败返回None
        """
        if not bounds_str:
            return None

        # 格式1: [left,top][right,bottom] (Android 风格)
        match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)
        if match:
            left = int(match.group(1))
            top = int(match.group(2))
            right = int(match.group(3))
            bottom = int(match.group(4))
            return (left, top, right - left, bottom - top)

        # 格式2: RectT (x, y) - [width x height] (HarmonyOS FrameRect 格式)
        match = re.match(r'RectT\s*\(\s*([\d.]+)\s*,\s*([\d.]+)\s*\)\s*-\s*\[\s*([\d.]+)\s*x\s*([\d.]+)\s*\]', bounds_str)
        if match:
            return (
                int(float(match.group(1))),
                int(float(match.group(2))),
                int(float(match.group(3))),
                int(float(match.group(4)))
            )

        # 格式3: [x y width height] (HarmonyOS Bounds 格式，空格分隔)
        match = re.match(r'\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\]', bounds_str)
        if match:
            return (
                int(float(match.group(1))),
                int(float(match.group(2))),
                int(float(match.group(3))),
                int(float(match.group(4)))
            )

        return None

    @staticmethod
    def calculate_center(bounds: Tuple[int, int, int, int]) -> Tuple[int, int]:
        """
        计算bounds的中心点坐标

        Args:
            bounds: (left, top, width, height) 元组

        Returns:
            (x, y) 中心点坐标
        """
        left, top, width, height = bounds
        x = left + width // 2
        y = top + height // 2
        return (x, y)

    @staticmethod
    def bounds_to_center(bounds_str: str) -> Optional[Tuple[int, int]]:
        """
        从bounds字符串计算中心点坐标

        Args:
            bounds_str: bounds字符串，支持多种格式

        Returns:
            (x, y) 中心点坐标，解析失败返回None
        """
        bounds = UIOperations.parse_bounds(bounds_str)
        if bounds:
            return UIOperations.calculate_center(bounds)
        return None

    # ========================================================================
    # 元素查找
    # ========================================================================

    def find_element_in_tree(self, ui_tree: Dict[str, Any],
                             text: str = None,
                             element_type: str = None,
                             element_id: str = None) -> List[Dict[str, Any]]:
        """
        在UI树中查找元素（支持 -inspector 格式，坐标为屏幕绝对坐标）

        Args:
            ui_tree: UI树结构（从get_ui_tree返回）
            text: 元素文本（模糊匹配）
            element_type: 元素类型（如 Button, Text 等）
            element_id: 元素ID

        Returns:
            匹配的元素列表，每个元素包含屏幕绝对坐标（可直接用于点击）
        """
        results = []

        def search_nodes(nodes: List[Dict], depth: int = 0):
            for node in nodes:
                match = True

                # 检查类型
                if element_type and node.get('type') != element_type:
                    match = False

                # 检查文本（-inspector 格式使用小写 'text' 属性）
                if text and match:
                    props = node.get('properties', {})
                    node_text = str(props.get('text', ''))
                    if text.lower() not in node_text.lower():
                        match = False

                # 检查ID
                if element_id and match:
                    node_id = node.get('properties', {}).get('ID', '')
                    if str(element_id) != str(node_id):
                        match = False

                if match and (text or element_type or element_id):
                    props = node.get('properties', {})

                    # -inspector 格式直接提供 top, left, width, height（屏幕绝对坐标）
                    top = props.get('top', 0)
                    left = props.get('left', 0)
                    width = props.get('width', 0)
                    height = props.get('height', 0)

                    # 计算中心点（屏幕绝对坐标，可直接用于 uitest uiInput click）
                    center_x = int(left + width / 2)
                    center_y = int(top + height / 2)

                    element_info = {
                        'type': node.get('type'),
                        'text': props.get('text', ''),
                        'id': props.get('ID', ''),
                        'compid': props.get('compid', ''),
                        'top': top,
                        'left': left,
                        'width': width,
                        'height': height,
                        'x': center_x,  # 屏幕绝对坐标
                        'y': center_y,  # 屏幕绝对坐标
                        'visible': props.get('visible', False),
                        'clickable': props.get('clickable', False),
                        'depth': depth
                    }

                    results.append(element_info)

                # 递归搜索子节点
                if 'children' in node:
                    search_nodes(node['children'], depth + 1)

        # 开始搜索
        nodes = ui_tree.get('ui_tree', {}).get('nodes', [])
        if not nodes:
            nodes = ui_tree.get('nodes', [])

        search_nodes(nodes)

        logger.info(f"找到 {len(results)} 个匹配元素")
        return results

    def find_element(self, device_id: str,
                     text: str = None,
                     element_type: str = None,
                     element_id: str = None,
                     bundle_name: str = None,
                     window_id: int = None) -> Dict[str, Any]:
        """
        在设备上查找元素（获取UI树并搜索）

        Args:
            device_id: 设备ID
            text: 元素文本
            element_type: 元素类型
            element_id: 元素ID
            bundle_name: 应用包名（用于定位窗口）
            window_id: 窗口ID

        Returns:
            查找结果，包含匹配的元素列表
        """
        from .uitree_parser import UITreeParser

        # 确定窗口ID
        target_window_id = window_id

        if not target_window_id:
            if bundle_name:
                target_window_id = self.hdc.find_window_by_bundle(device_id, bundle_name)

            if not target_window_id:
                # 获取第一个可见窗口
                window_list = self.hdc.get_window_list(device_id)
                if window_list['success'] and window_list['windows']:
                    for window in window_list['windows']:
                        if window['is_visible']:
                            target_window_id = window['window_id']
                            break

        if not target_window_id:
            return {
                'success': False,
                'error': '未找到可用窗口'
            }

        # 获取UI树
        ui_tree_result = self.hdc.get_ui_tree_raw(device_id, target_window_id)
        if not ui_tree_result['success']:
            return {
                'success': False,
                'error': ui_tree_result.get('error', '获取UI树失败')
            }

        # 解析UI树
        parser = UITreeParser()
        parsed_tree = parser.parse(ui_tree_result['ui_tree'])

        # 搜索元素
        elements = self.find_element_in_tree(
            {'nodes': parsed_tree['nodes']},
            text=text,
            element_type=element_type,
            element_id=element_id
        )

        return {
            'success': True,
            'device_id': device_id,
            'window_id': target_window_id,
            'elements': elements,
            'count': len(elements)
        }

