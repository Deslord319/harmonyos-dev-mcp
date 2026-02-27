"""
工具基类（设备扩展）

继承 common 的通用 ToolBase，
添加设备相关方法 (get_device_id, with_device)。
"""
import functools
import inspect
from typing import Optional, Tuple, Union
from loguru import logger

from common.tools.base import ToolBase as _CommonToolBase
from ..container import get_hdc


class ToolBase(_CommonToolBase):
    """
    工具基类（含设备操作）

    继承 common 的通用方法，扩展：
    - 设备 ID 获取和验证
    - 设备自动解析装饰器
    """

    @staticmethod
    def get_device_id(device_id: Optional[str] = None) -> Tuple[bool, Union[str, dict]]:
        """
        获取有效的设备ID

        Args:
            device_id: 指定的设备ID，为 None 时使用第一个设备

        Returns:
            (成功, 设备ID) 或 (失败, 错误字典)

        Example:
            ok, device = ToolBase.get_device_id(device_id)
            if not ok:
                return device  # 返回错误字典
            # 使用 device 继续操作
        """
        if device_id:
            return True, device_id

        try:
            hdc = get_hdc()
            devices = hdc.list_devices()

            if not devices:
                return False, {
                    'success': False,
                    'error': '没有找到连接的设备',
                    'error_code': 'DEVICE_NOT_FOUND'
                }

            return True, devices[0]
        except Exception as e:
            logger.error(f"获取设备列表失败: {e}")
            return False, {
                'success': False,
                'error': str(e),
                'error_code': 'DEVICE_LIST_ERROR'
            }

    @staticmethod
    def with_device(**error_fields):
        """
        设备解析装饰器（支持 async/sync）

        自动解析函数的 device_id 参数：
        - 如果已指定 device_id，直接使用
        - 如果为 None，自动获取第一个设备
        - 解析失败时返回标准错误字典（合并 error_fields）

        解析成功后，device_id 参数的值被替换为实际设备ID字符串。

        Args:
            **error_fields: 设备解析失败时补充到错误结果的默认字段

        Example:
            @mcp_tool(category="packages")
            @ToolBase.handle_tool_error('LIST_PACKAGES_ERROR', packages=[], count=0)
            @ToolBase.with_device(packages=[], count=0)
            async def list_packages(device_id: str = None, keyword: str = None):
                hdc = get_hdc()
                result = await asyncio.to_thread(hdc.list_packages, device_id, keyword)
                return result
        """
        def decorator(func):
            if inspect.iscoroutinefunction(func):
                @functools.wraps(func)
                async def async_wrapper(*args, **kwargs):
                    device_id = kwargs.get('device_id')
                    ok, device = ToolBase.get_device_id(device_id)
                    if not ok:
                        for k, v in error_fields.items():
                            device.setdefault(k, v)
                        return device
                    kwargs['device_id'] = device
                    return await func(*args, **kwargs)
                return async_wrapper
            else:
                @functools.wraps(func)
                def wrapper(*args, **kwargs):
                    device_id = kwargs.get('device_id')
                    ok, device = ToolBase.get_device_id(device_id)
                    if not ok:
                        for k, v in error_fields.items():
                            device.setdefault(k, v)
                        return device
                    kwargs['device_id'] = device
                    return func(*args, **kwargs)
                return wrapper
        return decorator
