"""
设备管理工具

提供设备列表、hilog 文件获取、截图等功能。
"""
import asyncio
import os
from typing import Optional, Dict
from datetime import datetime
from loguru import logger

from ..container import get_hdc
from ..types import ListDevicesResult, HilogReceiveResult
from .base import ToolBase
from .registry import mcp_tool


@mcp_tool(category="device")
@ToolBase.handle_tool_error('DEVICE_LIST_ERROR', devices=[], count=0)
async def list_devices() -> ListDevicesResult:
    """
    列出所有连接的HarmonyOS设备和模拟器
    
    Returns:
        包含设备列表的字典:
        - success: 是否成功
        - devices: 设备ID列表
        - count: 设备数量
    """
    hdc = get_hdc()
    devices = await asyncio.to_thread(hdc.list_devices)
    
    return {
        'success': True,
        'devices': devices,
        'count': len(devices)
    }


@mcp_tool(category="device")
@ToolBase.handle_tool_error('HILOG_RECEIVE_ERROR', files=[], total_size=0)
@ToolBase.with_device(files=[], total_size=0)
@ToolBase.validate_params(local_dir=['path'])
async def hilog_receive(device_id: Optional[str] = None, local_dir: Optional[str] = None) -> HilogReceiveResult:
    """
    从HarmonyOS设备的 /data/log/hilog 目录中获取所有 hilog 日志文件和 dict 解密文件

    Args:
        device_id: 设备ID，如果为None则使用第一个设备
        local_dir: 本地保存目录，如果为None则使用当前工作目录

    Returns:
        包含获取结果、文件列表和统计信息的字典
    """
    hdc = get_hdc()
    result = await asyncio.to_thread(hdc.hilog_receive, device_id, local_dir)
    
    # 添加设备ID到结果
    result['device_id'] = device_id
    
    # 确保必需字段存在
    if 'files' not in result:
        result['files'] = []
    if 'total_size' not in result:
        result['total_size'] = 0
    
    return result


@mcp_tool(category="device")
@ToolBase.handle_tool_error('SCREENSHOT_ERROR')
@ToolBase.with_device()
@ToolBase.validate_params(local_path=['path'])
async def take_screenshot(
    device_id: Optional[str] = None,
    local_path: Optional[str] = None,
    display_id: int = 0
) -> dict:
    """
    对设备屏幕进行截图

    Args:
        device_id: 设备ID，如果为None则使用第一个设备
        local_path: 本地保存路径，如果为None则自动生成路径（./screenshots/screenshot_时间戳.png）
        display_id: 显示器ID，默认为主屏幕(0)

    Returns:
        包含截图结果的字典:
        - success: 是否成功
        - local_path: 本地文件路径
        - file_size: 文件大小（字节）
        - device_id: 设备ID
    """
    hdc = get_hdc()
    
    # 如果未指定保存路径，自动生成
    if not local_path:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        screenshots_dir = './screenshots'
        os.makedirs(screenshots_dir, exist_ok=True)
        local_path = os.path.join(screenshots_dir, f'screenshot_{timestamp}.png')
    
    result = await asyncio.to_thread(
        hdc.take_screenshot,
        device_id,
        local_path,
        display_id
    )
    
    return result


@mcp_tool(category="device")
@ToolBase.handle_tool_error('ELEMENT_SCREENSHOT_ERROR')
@ToolBase.with_device()
@ToolBase.validate_params(local_path=['path'])
async def take_element_screenshot(
    device_id: Optional[str] = None,
    local_path: Optional[str] = None,
    left: int = 0,
    top: int = 0,
    right: int = 0,
    bottom: int = 0
) -> dict:
    """
    对指定元素区域进行截图

    先进行全屏截图，然后裁剪指定区域。需要安装 Pillow 库才能裁剪，
    否则返回全屏截图。

    Args:
        device_id: 设备ID，如果为None则使用第一个设备
        local_path: 本地保存路径，如果为None则自动生成
        left: 元素左边界 X 坐标
        top: 元素上边界 Y 坐标
        right: 元素右边界 X 坐标
        bottom: 元素下边界 Y 坐标

    Returns:
        包含截图结果的字典:
        - success: 是否成功
        - local_path: 本地文件路径
        - file_size: 文件大小（字节）
        - bounds: 裁剪区域边界
    """
    hdc = get_hdc()
    
    # 如果未指定保存路径，自动生成
    if not local_path:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        screenshots_dir = './screenshots'
        os.makedirs(screenshots_dir, exist_ok=True)
        local_path = os.path.join(screenshots_dir, f'element_{timestamp}.png')
    
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
    
    return result

