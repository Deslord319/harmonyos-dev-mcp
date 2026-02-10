"""
UI 操作工具

提供点击、滑动、输入、按键等 UI 自动化操作。
"""
from typing import Optional
from loguru import logger

from ..container import get_hdc, get_ui_operations
from ..types import ClickResult, SwipeResult, InputTextResult, PressKeyResult, FindElementResult
from .base import ToolBase
from .registry import mcp_tool


@mcp_tool(category="ui")
def click_element(
    device_id: str = None,
    x: int = None,
    y: int = None,
    text: str = None,
    element_type: str = None,
    double_click: bool = False,
    bundle_name: str = None
) -> dict:
    """
    点击屏幕上的元素

    Args:
        device_id: 设备ID，如果为None则使用第一个设备
        x: X坐标（与text/element_type二选一）
        y: Y坐标（与text/element_type二选一）
        text: 元素文本（自动查找元素并点击）
        element_type: 元素类型（如Button、Text等）
        double_click: 是否双击
        bundle_name: 应用包名（用于定位窗口，提高查找准确性）

    Returns:
        操作结果
    """
    default_result = {'x': x or 0, 'y': y or 0}
    
    try:
        ok, device = ToolBase.get_device_id(device_id)
        if not ok:
            device.update(default_result)
            return device

        ui_ops = get_ui_operations()

        # 如果提供了坐标，直接点击
        if x is not None and y is not None:
            if double_click:
                return ui_ops.double_click(device, x, y)
            else:
                return ui_ops.click(device, x, y)

        # 如果提供了text或element_type，先查找元素
        if text or element_type:
            result = ui_ops.find_element(
                device, text=text, element_type=element_type, bundle_name=bundle_name
            )
            if not result['success']:
                result.update(default_result)
                return result
            if not result['elements']:
                return {
                    'success': False,
                    'error': f'未找到匹配的元素: text={text}, type={element_type}',
                    'error_code': 'ELEMENT_NOT_FOUND',
                    **default_result
                }

            # 使用第一个匹配的元素
            element = result['elements'][0]
            if 'x' not in element or 'y' not in element:
                return {
                    'success': False,
                    'error': f'元素没有有效的坐标信息: {element}',
                    'error_code': 'INVALID_ELEMENT_COORDS',
                    **default_result
                }

            if double_click:
                return ui_ops.double_click(device, element['x'], element['y'])
            else:
                return ui_ops.click(device, element['x'], element['y'])

        return {
            'success': False,
            'error': '必须提供坐标(x, y)或查找条件(text/element_type)',
            'error_code': 'MISSING_PARAMS',
            **default_result
        }

    except Exception as e:
        error_result = ToolBase.wrap_error(e, 'CLICK_ERROR')
        error_result.update(default_result)
        return error_result


@mcp_tool(category="ui")
def long_press_element(
    device_id: str = None,
    x: int = None,
    y: int = None,
    text: str = None,
    element_type: str = None,
    bundle_name: str = None
) -> dict:
    """
    长按屏幕上的元素

    Args:
        device_id: 设备ID，如果为None则使用第一个设备
        x: X坐标
        y: Y坐标
        text: 元素文本（自动查找元素并长按）
        element_type: 元素类型
        bundle_name: 应用包名（用于定位窗口）

    Returns:
        操作结果
    """
    try:
        ok, device = ToolBase.get_device_id(device_id)
        if not ok:
            return device

        ui_ops = get_ui_operations()

        # 如果提供了坐标，直接长按
        if x is not None and y is not None:
            return ui_ops.long_click(device, x, y)

        # 查找元素
        if text or element_type:
            result = ui_ops.find_element(
                device, text=text, element_type=element_type, bundle_name=bundle_name
            )
            if not result['success']:
                return result
            if not result['elements']:
                return {
                    'success': False,
                    'error': '未找到匹配的元素',
                    'error_code': 'ELEMENT_NOT_FOUND'
                }

            element = result['elements'][0]
            if 'x' not in element or 'y' not in element:
                return {
                    'success': False,
                    'error': '元素没有有效的坐标信息',
                    'error_code': 'INVALID_ELEMENT_COORDS'
                }

            return ui_ops.long_click(device, element['x'], element['y'])

        return {
            'success': False,
            'error': '必须提供坐标或查找条件',
            'error_code': 'MISSING_PARAMS'
        }

    except Exception as e:
        return ToolBase.wrap_error(e, 'LONG_PRESS_ERROR')


@mcp_tool(category="ui")
def swipe(
    device_id: str = None,
    from_x: int = None,
    from_y: int = None,
    to_x: int = None,
    to_y: int = None,
    direction: str = None,
    speed: int = 600
) -> SwipeResult:
    """
    滑动操作

    Args:
        device_id: 设备ID，如果为None则使用第一个设备
        from_x: 起点X坐标（与direction二选一）
        from_y: 起点Y坐标
        to_x: 终点X坐标
        to_y: 终点Y坐标
        direction: 滑动方向 (left/right/up/down)，与坐标二选一
        speed: 滑动速度 (200-40000, 默认600)

    Returns:
        操作结果
    """
    default_result = {
        'from_x': from_x or 0,
        'from_y': from_y or 0,
        'to_x': to_x or 0,
        'to_y': to_y or 0,
        'direction': direction
    }
    
    try:
        ok, device = ToolBase.get_device_id(device_id)
        if not ok:
            device.update(default_result)
            return device

        ui_ops = get_ui_operations()

        # 如果提供了方向，使用方向滑动
        if direction:
            return ui_ops.swipe_direction(device, direction, speed)

        # 如果提供了坐标，使用坐标滑动
        if all(v is not None for v in [from_x, from_y, to_x, to_y]):
            return ui_ops.swipe(device, from_x, from_y, to_x, to_y, speed)

        return {
            'success': False,
            'error': '必须提供滑动坐标(from_x, from_y, to_x, to_y)或方向(direction)',
            'error_code': 'MISSING_PARAMS',
            **default_result
        }

    except Exception as e:
        error_result = ToolBase.wrap_error(e, 'SWIPE_ERROR')
        error_result.update(default_result)
        return error_result


@mcp_tool(category="ui")
def input_text(
    device_id: str = None,
    x: int = None,
    y: int = None,
    text: str = None,
    element_text: str = None,
    element_type: str = None,
    bundle_name: str = None
) -> InputTextResult:
    """
    在输入框中输入文本

    Args:
        device_id: 设备ID，如果为None则使用第一个设备
        x: 输入框X坐标
        y: 输入框Y坐标
        text: 要输入的文本内容
        element_text: 输入框元素的文本（用于自动查找）
        element_type: 输入框元素类型（如TextInput）
        bundle_name: 应用包名（用于定位窗口）

    Returns:
        操作结果
    """
    default_result = {
        'text': text or '',
        'x': x or 0,
        'y': y or 0
    }
    
    try:
        ok, device = ToolBase.get_device_id(device_id)
        if not ok:
            device.update(default_result)
            return device

        if not text:
            return {
                'success': False,
                'error': '必须提供要输入的文本(text)',
                'error_code': 'MISSING_TEXT',
                **default_result
            }

        ui_ops = get_ui_operations()

        # 如果提供了坐标，直接输入
        if x is not None and y is not None:
            return ui_ops.input_text(device, x, y, text)

        # 查找元素
        if element_text or element_type:
            result = ui_ops.find_element(
                device, text=element_text, element_type=element_type, bundle_name=bundle_name
            )
            if not result['success']:
                result.update(default_result)
                return result
            if not result['elements']:
                return {
                    'success': False,
                    'error': '未找到匹配的输入框',
                    'error_code': 'ELEMENT_NOT_FOUND',
                    **default_result
                }

            element = result['elements'][0]
            if 'x' not in element or 'y' not in element:
                return {
                    'success': False,
                    'error': '元素没有有效的坐标信息',
                    'error_code': 'INVALID_ELEMENT_COORDS',
                    **default_result
                }

            return ui_ops.input_text(device, element['x'], element['y'], text)

        return {
            'success': False,
            'error': '必须提供坐标或查找条件',
            'error_code': 'MISSING_PARAMS',
            **default_result
        }

    except Exception as e:
        error_result = ToolBase.wrap_error(e, 'INPUT_TEXT_ERROR')
        error_result.update(default_result)
        return error_result


@mcp_tool(category="ui")
def press_key(device_id: str = None, key: str = None) -> PressKeyResult:
    """
    模拟按键操作

    Args:
        device_id: 设备ID，如果为None则使用第一个设备
        key: 按键名称 (Home/Back/Enter等)

    Returns:
        操作结果
    """
    default_result = {'key': key or ''}
    
    try:
        ok, device = ToolBase.get_device_id(device_id)
        if not ok:
            device.update(default_result)
            return device

        if not key:
            return {
                'success': False,
                'error': '必须提供按键名称(key)',
                'error_code': 'MISSING_KEY',
                **default_result
            }

        ui_ops = get_ui_operations()
        return ui_ops.press_key(device, key)

    except Exception as e:
        error_result = ToolBase.wrap_error(e, 'PRESS_KEY_ERROR')
        error_result.update(default_result)
        return error_result


@mcp_tool(category="ui")
def find_element(
    device_id: str = None,
    text: str = None,
    element_type: str = None,
    element_id: str = None,
    bundle_name: str = None
) -> FindElementResult:
    """
    在UI树中查找元素

    Args:
        device_id: 设备ID，如果为None则使用第一个设备
        text: 元素文本（模糊匹配）
        element_type: 元素类型（如Button、Text、Image等）
        element_id: 元素ID
        bundle_name: 应用包名（用于定位窗口）

    Returns:
        匹配的元素列表，包含坐标信息
    """
    default_result = {'elements': [], 'count': 0}
    
    try:
        ok, device = ToolBase.get_device_id(device_id)
        if not ok:
            device.update(default_result)
            return device

        if not any([text, element_type, element_id]):
            return {
                'success': False,
                'error': '必须提供至少一个查找条件(text/element_type/element_id)',
                'error_code': 'MISSING_SEARCH_CRITERIA',
                **default_result
            }

        ui_ops = get_ui_operations()
        result = ui_ops.find_element(
            device,
            text=text,
            element_type=element_type,
            element_id=element_id,
            bundle_name=bundle_name
        )
        
        # 确保必需字段存在
        if 'elements' not in result:
            result['elements'] = []
        if 'count' not in result:
            result['count'] = len(result['elements'])
        
        return result

    except Exception as e:
        error_result = ToolBase.wrap_error(e, 'FIND_ELEMENT_ERROR')
        error_result.update(default_result)
        return error_result
