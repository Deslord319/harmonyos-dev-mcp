"""
UI 树工具

提供 UI 组件树获取和窗口列表查询功能。
"""
import json
from typing import Optional
from loguru import logger

from ..container import get_hdc
from ..utils.uitree_parser import UITreeParser
from ..types import UITreeResult, ListWindowsResult
from .base import ToolBase
from .registry import mcp_tool


def _ensure_json_serializable(obj, max_depth: int = 50, current_depth: int = 0):
    """
    确保对象可以被安全地序列化为 JSON（迭代方式，避免递归深度问题）
    
    Args:
        obj: 要检查的对象
        max_depth: 最大深度（仅作为备用保护）
        current_depth: 当前深度
        
    Returns:
        安全的可序列化对象
    """
    # 使用迭代方式处理，避免递归深度限制
    import copy
    
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    
    # 深拷贝避免修改原对象
    try:
        result = copy.deepcopy(obj)
    except RecursionError:
        # 如果 deepcopy 也失败，回退到迭代式复制
        result = _iterative_deep_copy(obj)
    
    return result


def _iterative_deep_copy(obj):
    """
    迭代式深拷贝，避免递归深度限制
    
    使用栈来模拟递归，可以处理任意深度的嵌套结构
    """
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    
    # 创建根容器
    if isinstance(obj, dict):
        root = {}
    elif isinstance(obj, (list, tuple)):
        root = []
    else:
        return str(obj)
    
    # 栈: (源对象, 目标容器, 父容器, 键/索引)
    # 使用显式栈代替递归
    stack = [(obj, root, None, None)]
    
    while stack:
        src, dst, parent, key = stack.pop()
        
        if isinstance(src, dict):
            if dst is None:
                dst = {}
                if parent is not None:
                    if isinstance(parent, dict):
                        parent[key] = dst
                    else:
                        parent.append(dst)
            
            for k, v in src.items():
                if v is None or isinstance(v, (bool, int, float, str)):
                    dst[k] = v
                elif isinstance(v, dict):
                    child = {}
                    dst[k] = child
                    stack.append((v, child, None, None))
                elif isinstance(v, (list, tuple)):
                    child = []
                    dst[k] = child
                    stack.append((v, child, None, None))
                else:
                    dst[k] = str(v)
                    
        elif isinstance(src, (list, tuple)):
            if dst is None:
                dst = []
                if parent is not None:
                    if isinstance(parent, dict):
                        parent[key] = dst
                    else:
                        parent.append(dst)
            
            # 反向遍历保持顺序
            for item in reversed(src):
                if item is None or isinstance(item, (bool, int, float, str)):
                    dst.insert(0, item)
                elif isinstance(item, dict):
                    child = {}
                    dst.insert(0, child)
                    stack.append((item, child, None, None))
                elif isinstance(item, (list, tuple)):
                    child = []
                    dst.insert(0, child)
                    stack.append((item, child, None, None))
                else:
                    dst.insert(0, str(item))
    
    return root


@mcp_tool(category="ui_tree")
def get_ui_tree(
    device_id: str = None,
    bundle_name: str = None,
    window_id: int = None
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
    default_result = {
        'window_id': window_id or 0,
        'ui_tree': {},
        'node_count': 0
    }
    
    try:
        ok, device = ToolBase.get_device_id(device_id)
        if not ok:
            device.update(default_result)
            return device

        hdc = get_hdc()

        # 确定窗口ID
        target_window_id = window_id

        if not target_window_id:
            if bundle_name:
                # 根据包名查找窗口
                target_window_id = hdc.find_window_by_bundle(device, bundle_name)
                if not target_window_id:
                    return {
                        'success': False,
                        'device_id': device,
                        'error': f'未找到应用 {bundle_name} 的窗口',
                        'error_code': 'WINDOW_NOT_FOUND',
                        **default_result
                    }
            else:
                # 获取窗口列表，使用第一个可见窗口
                window_list = hdc.get_window_list(device)
                if not window_list['success'] or not window_list['windows']:
                    return {
                        'success': False,
                        'device_id': device,
                        'error': '未找到任何窗口',
                        'error_code': 'NO_WINDOWS',
                        **default_result
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
        ui_tree_result = hdc.get_ui_tree_raw(device, target_window_id)

        if not ui_tree_result['success']:
            return {
                'success': False,
                'device_id': device,
                'error': ui_tree_result.get('error', '获取UI树失败'),
                'error_code': 'UI_TREE_FETCH_ERROR',
                'window_id': target_window_id,
                'ui_tree': {},
                'node_count': 0
            }

        # 解析UI树
        parser = UITreeParser()
        parsed_tree = parser.parse(ui_tree_result['ui_tree'])

        # 确保结果可以安全序列化为 JSON（防止循环引用错误）
        safe_tree = _ensure_json_serializable(parsed_tree)

        return {
            'success': True,
            'device_id': device,
            'window_id': target_window_id,
            'ui_tree': safe_tree,
            'node_count': safe_tree.get('count', 0) if isinstance(safe_tree, dict) else 0
        }

    except Exception as e:
        error_result = ToolBase.wrap_error(e, 'GET_UI_TREE_ERROR')
        error_result.update(default_result)
        return error_result


@mcp_tool(category="ui_tree")
def list_windows(device_id: str = None) -> ListWindowsResult:
    """
    列出设备上的所有窗口

    Args:
        device_id: 设备ID，如果为None则使用第一个设备

    Returns:
        窗口列表
    """
    default_result = {'windows': [], 'count': 0}
    
    try:
        ok, device = ToolBase.get_device_id(device_id)
        if not ok:
            device.update(default_result)
            return device

        hdc = get_hdc()
        result = hdc.get_window_list(device)
        
        # 确保必需字段存在
        result['device_id'] = device
        if 'windows' not in result:
            result['windows'] = []
        if 'count' not in result:
            result['count'] = len(result['windows'])

        return result

    except Exception as e:
        error_result = ToolBase.wrap_error(e, 'LIST_WINDOWS_ERROR')
        error_result.update(default_result)
        return error_result
