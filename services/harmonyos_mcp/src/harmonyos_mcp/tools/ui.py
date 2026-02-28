"""
UI 操作工具

提供点击、滑动、输入、按键、截图等 UI 自动化操作。
"""
import asyncio
import os
from datetime import datetime
from typing import Optional, Tuple, Union
from loguru import logger

from ..container import get_hdc, get_ui_operations
from ..types import (
    ClickResult, LongPressResult, DragResult, SwipeResult, InputTextResult,
    PressKeyResult, FindElementResult, ScreenshotResult, ElementScreenshotResult
)
from .device_base import ToolBase
from common.tools.registry import mcp_tool


async def _resolve_element_coords(
    device_id: str,
    text: Optional[str] = None,
    element_type: Optional[str] = None,
    bundle_name: Optional[str] = None,
) -> Tuple[bool, Union[Tuple[int, int], dict]]:
    """
    通过文本/类型查找元素并返回中心坐标
    
    Returns:
        (True, (x, y)) 成功时
        (False, error_dict) 失败时
    """
    ui_ops = get_ui_operations()
    result = await asyncio.to_thread(
        ui_ops.find_element, device_id,
        text=text, element_type=element_type, bundle_name=bundle_name
    )
    if not result['success']:
        return False, result
    if not result['elements']:
        return False, {
            'success': False,
            'error': f'未找到匹配的元素: text={text}, type={element_type}',
            'error_code': 'ELEMENT_NOT_FOUND'
        }

    element = result['elements'][0]
    if 'x' not in element or 'y' not in element:
        return False, {
            'success': False,
            'error': f'元素没有有效的坐标信息: {element}',
            'error_code': 'INVALID_ELEMENT_COORDS'
        }
    return True, (element['x'], element['y'])


@mcp_tool(category="ui")
@ToolBase.handle_tool_error('CLICK_ERROR', x=0, y=0)
@ToolBase.with_device(x=0, y=0)
async def click_element(
    device_id: Optional[str] = None,
    x: Optional[int] = None,
    y: Optional[int] = None,
    text: Optional[str] = None,
    element_type: Optional[str] = None,
    double_click: bool = False,
    bundle_name: Optional[str] = None
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
    has_coords = x is not None and y is not None
    has_search = text or element_type
    if has_coords and has_search:
        return {
            'success': False,
            'error': '不能同时提供坐标(x, y)和查找条件(text/element_type)，请二选一',
            'error_code': 'PARAM_CONFLICT',
            'x': x, 'y': y
        }

    ui_ops = get_ui_operations()

    if has_coords:
        if double_click:
            return await asyncio.to_thread(ui_ops.double_click, device_id, x, y)
        else:
            return await asyncio.to_thread(ui_ops.click, device_id, x, y)

    if has_search:
        ok, coords = await _resolve_element_coords(device_id, text=text, element_type=element_type, bundle_name=bundle_name)
        if not ok:
            coords.update({'x': x or 0, 'y': y or 0})
            return coords
        ex, ey = coords
        if double_click:
            return await asyncio.to_thread(ui_ops.double_click, device_id, ex, ey)
        else:
            return await asyncio.to_thread(ui_ops.click, device_id, ex, ey)

    return {
        'success': False,
        'error': '必须提供坐标(x, y)或查找条件(text/element_type)',
        'error_code': 'MISSING_PARAMS',
        'x': x or 0, 'y': y or 0
    }


@mcp_tool(category="ui")
@ToolBase.handle_tool_error('LONG_PRESS_ERROR')
@ToolBase.with_device()
async def long_press_element(
    device_id: Optional[str] = None,
    x: Optional[int] = None,
    y: Optional[int] = None,
    text: Optional[str] = None,
    element_type: Optional[str] = None,
    bundle_name: Optional[str] = None
) -> LongPressResult:
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
    ui_ops = get_ui_operations()

    if x is not None and y is not None:
        return await asyncio.to_thread(ui_ops.long_click, device_id, x, y)

    if text or element_type:
        ok, coords = await _resolve_element_coords(device_id, text=text, element_type=element_type, bundle_name=bundle_name)
        if not ok:
            return coords
        ex, ey = coords
        return await asyncio.to_thread(ui_ops.long_click, device_id, ex, ey)

    return {
        'success': False,
        'error': '必须提供坐标或查找条件',
        'error_code': 'MISSING_PARAMS'
    }


@mcp_tool(category="ui")
@ToolBase.handle_tool_error('SWIPE_ERROR', from_x=0, from_y=0, to_x=0, to_y=0, direction=None)
@ToolBase.with_device(from_x=0, from_y=0, to_x=0, to_y=0, direction=None)
async def swipe(
    device_id: Optional[str] = None,
    from_x: Optional[int] = None,
    from_y: Optional[int] = None,
    to_x: Optional[int] = None,
    to_y: Optional[int] = None,
    direction: Optional[str] = None,
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

    ui_ops = get_ui_operations()

    if direction:
        return await asyncio.to_thread(ui_ops.swipe_direction, device_id, direction, speed)

    if all(v is not None for v in [from_x, from_y, to_x, to_y]):
        return await asyncio.to_thread(ui_ops.swipe, device_id, from_x, from_y, to_x, to_y, speed)

    return {
        'success': False,
        'error': '必须提供滑动坐标(from_x, from_y, to_x, to_y)或方向(direction)',
        'error_code': 'MISSING_PARAMS',
        **default_result
    }


@mcp_tool(category="ui")
@ToolBase.handle_tool_error('INPUT_TEXT_ERROR', text='', x=0, y=0)
@ToolBase.with_device(text='', x=0, y=0)
async def input_text(
    device_id: Optional[str] = None,
    x: Optional[int] = None,
    y: Optional[int] = None,
    text: Optional[str] = None,
    element_text: Optional[str] = None,
    element_type: Optional[str] = None,
    bundle_name: Optional[str] = None
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

    if not text:
        return {
            'success': False,
            'error': '必须提供要输入的文本(text)',
            'error_code': 'MISSING_TEXT',
            **default_result
        }

    ui_ops = get_ui_operations()

    if x is not None and y is not None:
        return await asyncio.to_thread(ui_ops.input_text, device_id, x, y, text)

    if element_text or element_type:
        ok, coords = await _resolve_element_coords(device_id, text=element_text, element_type=element_type, bundle_name=bundle_name)
        if not ok:
            coords.update(default_result)
            return coords
        ex, ey = coords
        return await asyncio.to_thread(ui_ops.input_text, device_id, ex, ey, text)

    return {
        'success': False,
        'error': '必须提供坐标或查找条件',
        'error_code': 'MISSING_PARAMS',
        **default_result
    }


@mcp_tool(category="ui")
@ToolBase.handle_tool_error('PRESS_KEY_ERROR', key='')
@ToolBase.with_device(key='')
async def press_key(device_id: Optional[str] = None, key: Optional[str] = None) -> PressKeyResult:
    """
    模拟按键操作

    Args:
        device_id: 设备ID，如果为None则使用第一个设备
        key: 按键名称 (Home/Back/Enter等)

    Returns:
        操作结果
    """
    if not key:
        return {
            'success': False,
            'error': '必须提供按键名称(key)',
            'error_code': 'MISSING_KEY',
            'key': ''
        }

    ui_ops = get_ui_operations()
    return await asyncio.to_thread(ui_ops.press_key, device_id, key)


@mcp_tool(category="ui")
@ToolBase.handle_tool_error('FIND_ELEMENT_ERROR', elements=[], count=0)
@ToolBase.with_device(elements=[], count=0)
async def find_element(
    device_id: Optional[str] = None,
    text: Optional[str] = None,
    element_type: Optional[str] = None,
    element_id: Optional[str] = None,
    bundle_name: Optional[str] = None
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
    if not any([text, element_type, element_id]):
        return {
            'success': False,
            'error': '必须提供至少一个查找条件(text/element_type/element_id)',
            'error_code': 'MISSING_SEARCH_CRITERIA',
            'elements': [], 'count': 0
        }

    ui_ops = get_ui_operations()
    result = await asyncio.to_thread(
        ui_ops.find_element, device_id,
        text=text, element_type=element_type, element_id=element_id, bundle_name=bundle_name
    )
    
    if 'elements' not in result:
        result['elements'] = []
    if 'count' not in result:
        result['count'] = len(result['elements'])
    
    return result


@mcp_tool(category="ui")
@ToolBase.handle_tool_error('SCREENSHOT_ERROR')
@ToolBase.with_device()
@ToolBase.validate_params(local_path=['path'])
async def screenshot(
    device_id: Optional[str] = None,
    local_path: Optional[str] = None,
    display_id: int = 0,
    left: Optional[int] = None,
    top: Optional[int] = None,
    right: Optional[int] = None,
    bottom: Optional[int] = None
) -> ScreenshotResult:
    """
    对设备屏幕进行截图（支持全屏截图和区域截图）

    Args:
        device_id: 设备ID，如果为None则使用第一个设备
        local_path: 本地保存路径，如果为None则自动生成路径
        display_id: 显示器ID，默认为主屏幕(0)
        left: 裁剪区域左边界 X 坐标（可选）
        top: 裁剪区域上边界 Y 坐标（可选）
        right: 裁剪区域右边界 X 坐标（可选）
        bottom: 裁剪区域下边界 Y 坐标（可选）

    Returns:
        包含截图结果的字典:
        - success: 是否成功
        - local_path: 本地文件路径
        - file_size: 文件大小（字节）
        - device_id: 设备ID
        - bounds: 裁剪区域边界（仅区域截图时返回）
    """
    hdc = get_hdc()

    if not local_path:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        screenshots_dir = os.path.join(os.path.expanduser('~'), 'harmonyos-screenshots')
        os.makedirs(screenshots_dir, exist_ok=True)
        suffix = 'element' if left is not None else 'screenshot'
        local_path = os.path.join(screenshots_dir, f'{suffix}_{timestamp}.jpeg')

    if left is not None and top is not None and right is not None and bottom is not None:
        bounds = {
            'left': left,
            'top': top,
            'right': right,
            'bottom': bottom
        }
        result = await asyncio.to_thread(
            hdc.take_element_screenshot,
            device_id,
            local_path,
            bounds
        )
        result['bounds'] = bounds
        return result
    else:
        result = await asyncio.to_thread(
            hdc.take_screenshot,
            device_id,
            local_path,
            display_id
        )
        return result


@mcp_tool(category="ui")
@ToolBase.handle_tool_error('DRAG_ERROR')
@ToolBase.with_device()
async def drag(
    device_id: Optional[str] = None,
    from_x: Optional[int] = None,
    from_y: Optional[int] = None,
    to_x: Optional[int] = None,
    to_y: Optional[int] = None,
    speed: int = 600
) -> DragResult:
    """
    拖拽操作

    Args:
        device_id: 设备ID，如果为None则使用第一个设备
        from_x: 起点X坐标
        from_y: 起点Y坐标
        to_x: 终点X坐标
        to_y: 终点Y坐标
        speed: 拖拽速度 (200-40000, 默认600)

    Returns:
        操作结果
    """
    if not all(v is not None for v in [from_x, from_y, to_x, to_y]):
        return {
            'success': False,
            'error': '必须提供完整的坐标(from_x, from_y, to_x, to_y)',
            'error_code': 'MISSING_PARAMS'
        }

    ui_ops = get_ui_operations()
    return await asyncio.to_thread(ui_ops.drag, device_id, from_x, from_y, to_x, to_y, speed)
