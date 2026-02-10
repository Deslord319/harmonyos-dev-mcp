"""
设备管理工具

提供设备列表、hilog 文件获取等功能。
"""
from typing import Optional
from loguru import logger

from ..container import get_hdc
from ..types import ListDevicesResult, HilogReceiveResult
from .base import ToolBase
from .registry import mcp_tool


@mcp_tool(category="device")
@ToolBase.handle_tool_error('DEVICE_LIST_ERROR', devices=[], count=0)
def list_devices() -> ListDevicesResult:
    """
    列出所有连接的HarmonyOS设备和模拟器
    
    Returns:
        包含设备列表的字典:
        - success: 是否成功
        - devices: 设备ID列表
        - count: 设备数量
    """
    hdc = get_hdc()
    devices = hdc.list_devices()
    
    return {
        'success': True,
        'devices': devices,
        'count': len(devices)
    }


@mcp_tool(category="device")
def hilog_receive(device_id: str = None, local_dir: str = None) -> dict:
    """
    从HarmonyOS设备的 /data/log/hilog 目录中获取所有 hilog 日志文件和 dict 解密文件

    Args:
        device_id: 设备ID，如果为None则使用第一个设备
        local_dir: 本地保存目录，如果为None则使用当前工作目录

    Returns:
        包含获取结果、文件列表和统计信息的字典
    """
    default_result = {
        'files': [],
        'total_size': 0
    }
    
    try:
        ok, device = ToolBase.get_device_id(device_id)
        if not ok:
            device.update(default_result)
            return device
        
        hdc = get_hdc()
        result = hdc.hilog_receive(device, local_dir)
        
        # 添加设备ID到结果
        result['device_id'] = device
        
        # 确保必需字段存在
        if 'files' not in result:
            result['files'] = []
        if 'total_size' not in result:
            result['total_size'] = 0
        
        return result
    except Exception as e:
        error_result = ToolBase.wrap_error(e, 'HILOG_RECEIVE_ERROR')
        error_result.update(default_result)
        return error_result
