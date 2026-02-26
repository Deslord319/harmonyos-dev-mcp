"""
UI 树工具

提供 UI 组件树获取和窗口列表查询功能。
"""
import asyncio
from typing import Optional
from loguru import logger

from ..container import get_hdc
from ..utils.uitree_parser import UITreeParser
from ..types import UITreeResult, ListWindowsResult
from .base import ToolBase
from .registry import mcp_tool


@mcp_tool(category="ui_tree")
@ToolBase.handle_tool_error('GET_UI_TREE_ERROR', window_id=0, ui_tree={}, node_count=0)
@ToolBase.with_device(window_id=0, ui_tree={}, node_count=0)
async def get_ui_tree(
    device_id: Optional[str] = None,
    bundle_name: Optional[str] = None,
    window_id: Optional[int] = None
) -> UITreeResult:
    """
    获取应用的UI组件树

    Args:
        device_id: 设备ID，如果为None则使用第一个设备
        bundle_name: 应用包名（可选，用于自动查找窗口）
        window_id: 窗口ID（可选，如果指定则直接使用该窗口）

    Returns:
        UI组件树JSON结构
    """
    hdc = get_hdc()

    # 确定窗口ID
    target_window_id = window_id

    if not target_window_id:
        if bundle_name:
            # 根据包名查找窗口
            target_window_id = await asyncio.to_thread(hdc.find_window_by_bundle, device_id, bundle_name)
            if not target_window_id:
                return {
                    'success': False,
                    'device_id': device_id,
                    'error': f'未找到应用 {bundle_name} 的窗口',
                    'error_code': 'WINDOW_NOT_FOUND',
                    'window_id': 0, 'ui_tree': {}, 'node_count': 0
                }
        else:
            # 获取窗口列表，使用第一个可见窗口
            window_list = await asyncio.to_thread(hdc.get_window_list, device_id)
            if not window_list['success'] or not window_list['windows']:
                return {
                    'success': False,
                    'device_id': device_id,
                    'error': '未找到任何窗口',
                    'error_code': 'NO_WINDOWS',
                    'window_id': 0, 'ui_tree': {}, 'node_count': 0
                }

            # 查找第一个可见窗口
            for window in window_list['windows']:
                if window['is_visible']:
                    target_window_id = window['window_id']
                    break

            if not target_window_id:
                # 如果没有可见窗口，使用第一个窗口
                target_window_id = window_list['windows'][0]['window_id']

    # 获取UI树原始数据
    ui_tree_result = await asyncio.to_thread(hdc.get_ui_tree_raw, device_id, target_window_id)

    if not ui_tree_result['success']:
        return {
            'success': False,
            'device_id': device_id,
            'error': ui_tree_result.get('error', '获取UI树失败'),
            'error_code': 'UI_TREE_FETCH_ERROR',
            'window_id': target_window_id,
            'ui_tree': {},
            'node_count': 0
        }

    # 解析UI树
    parser = UITreeParser()
    parsed_tree = parser.parse(ui_tree_result['ui_tree'])

    return {
        'success': True,
        'device_id': device_id,
        'window_id': target_window_id,
        'ui_tree': parsed_tree,
        'node_count': parsed_tree.get('count', 0) if isinstance(parsed_tree, dict) else 0
    }


@mcp_tool(category="ui_tree")
@ToolBase.handle_tool_error('LIST_WINDOWS_ERROR', windows=[], count=0)
@ToolBase.with_device(windows=[], count=0)
async def list_windows(device_id: Optional[str] = None) -> ListWindowsResult:
    """
    列出设备上的所有窗口

    Args:
        device_id: 设备ID，如果为None则使用第一个设备

    Returns:
        窗口列表
    """
    hdc = get_hdc()
    result = await asyncio.to_thread(hdc.get_window_list, device_id)
    
    # 确保必需字段存在
    result['device_id'] = device_id
    if 'windows' not in result:
        result['windows'] = []
    
    # 规范化窗口数据，使其符合 WindowInfo schema
    for w in result['windows']:
        w.setdefault('bundle_name', '')
        w.setdefault('is_visible', False)
        w.setdefault('bounds', {'left': 0, 'top': 0, 'right': 0, 'bottom': 0})
    
    if 'count' not in result:
        result['count'] = len(result['windows'])

    return result
