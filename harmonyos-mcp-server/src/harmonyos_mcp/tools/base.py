"""
工具基类

提供所有工具函数的公共方法，消除重复代码。
支持 async/sync 双模式装饰器，兼容 FastMCP 异步事件循环。
"""
import asyncio
import functools
import inspect
import os
import re
from typing import Optional, Tuple, Union
from loguru import logger

from ..container import get_hdc
from ..exceptions import DeviceNotFoundError


class ToolBase:
    """
    工具基类
    
    提供公共方法：
    - 设备 ID 获取和验证
    - 异常包装
    - 结果格式化
    - 路径与参数校验
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
    def ensure_device(device_id: Optional[str] = None) -> str:
        """
        确保获取到设备ID，否则抛出异常
        
        Args:
            device_id: 指定的设备ID
            
        Returns:
            有效的设备ID
            
        Raises:
            DeviceNotFoundError: 没有找到设备时
        """
        ok, result = ToolBase.get_device_id(device_id)
        if not ok:
            raise DeviceNotFoundError()
        return result
    
    @staticmethod
    def wrap_error(error: Exception, error_code: str = None) -> dict:
        """
        包装异常为标准错误响应
        
        Args:
            error: 异常对象
            error_code: 错误码（可选）
            
        Returns:
            标准化的错误响应字典
        """
        logger.error(f"操作失败: {error}")
        
        result = {
            'success': False,
            'error': str(error)
        }
        
        if error_code:
            result['error_code'] = error_code
        elif hasattr(error, 'code'):
            result['error_code'] = error.code
        
        return result
    
    @staticmethod
    def success_result(**kwargs) -> dict:
        """
        创建成功响应
        
        Args:
            **kwargs: 额外的响应字段
            
        Returns:
            成功响应字典
        """
        return {
            'success': True,
            **kwargs
        }
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """
        格式化持续时间
        
        Args:
            seconds: 秒数
            
        Returns:
            格式化的字符串
        """
        if seconds < 1:
            return f"{seconds * 1000:.0f}ms"
        elif seconds < 60:
            return f"{seconds:.2f}s"
        else:
            minutes = int(seconds // 60)
            secs = seconds % 60
            return f"{minutes}m {secs:.1f}s"

    @staticmethod
    def validate_path(path: str) -> bool:
        """
        校验路径安全性，防止路径遍历攻击
        
        检测 '..' 和 null 字节注入。
        
        Args:
            path: 待校验的路径字符串
            
        Returns:
            True 表示路径安全
            
        Raises:
            ValueError: 路径包含危险字符时
        """
        if '\x00' in path:
            raise ValueError(f"路径包含非法空字节: {path!r}")
        normalized = os.path.normpath(path)
        if '..' in normalized.split(os.sep):
            raise ValueError(f"路径包含目录遍历: {path!r}")
        return True

    @staticmethod
    def validate_params(**param_rules):
        """
        通用输入参数校验装饰器
        
        支持多种校验规则：
        - 'path': 路径安全校验（防止 .. 和空字节）
        - 'nonempty': 非空检查
        - 'max_length:N': 最大长度限制
        - 'int_range:min,max': 整数范围限制
        
        Args:
            **param_rules: 参数名 -> 规则列表的映射
            
        Example:
            @ToolBase.validate_params(local_dir=['path'], repo_url=['nonempty'])
            async def my_tool(local_dir: str, repo_url: str):
                ...
        """
        def decorator(func):
            def _do_validate(kwargs):
                for param_name, rules in param_rules.items():
                    value = kwargs.get(param_name)
                    if value is None:
                        continue
                    for rule in rules:
                        if rule == 'path' and isinstance(value, str):
                            ToolBase.validate_path(value)
                        elif rule == 'nonempty':
                            if not value:
                                raise ValueError(f"参数 '{param_name}' 不能为空")
                        elif rule.startswith('max_length:'):
                            max_len = int(rule.split(':')[1])
                            if isinstance(value, str) and len(value) > max_len:
                                raise ValueError(
                                    f"参数 '{param_name}' 长度 {len(value)} 超过最大限制 {max_len}"
                                )
                        elif rule.startswith('int_range:'):
                            parts = rule.split(':')[1].split(',')
                            lo, hi = int(parts[0]), int(parts[1])
                            if isinstance(value, int) and not (lo <= value <= hi):
                                raise ValueError(
                                    f"参数 '{param_name}' 值 {value} 超出范围 [{lo}, {hi}]"
                                )

            if inspect.iscoroutinefunction(func):
                @functools.wraps(func)
                async def async_wrapper(*args, **kwargs):
                    _do_validate(kwargs)
                    return await func(*args, **kwargs)
                return async_wrapper
            else:
                @functools.wraps(func)
                def sync_wrapper(*args, **kwargs):
                    _do_validate(kwargs)
                    return func(*args, **kwargs)
                return sync_wrapper
        return decorator

    @staticmethod
    def handle_tool_error(error_code: str, **default_fields):
        """
        工具函数错误处理装饰器（支持 async/sync）
        
        消除 try/except 样板代码。对于只需要简单异常包装的工具函数，
        可以用此装饰器替代手写 try/except。
        
        Args:
            error_code: 错误码（如 'WSL_CHECK_ERROR'）
            **default_fields: 错误时补充的默认字段
            
        Example:
            @mcp_tool(category="compile")
            @ToolBase.handle_tool_error('CLONE_ERROR')
            async def clone_library(repo_url: str) -> dict:
                manager = get_compile_manager()
                return await asyncio.to_thread(manager.clone_library, repo_url)
        """
        def decorator(func):
            if inspect.iscoroutinefunction(func):
                @functools.wraps(func)
                async def async_wrapper(*args, **kwargs):
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        error_result = ToolBase.wrap_error(e, error_code)
                        for k, v in default_fields.items():
                            error_result.setdefault(k, v)
                        return error_result
                return async_wrapper
            else:
                @functools.wraps(func)
                def wrapper(*args, **kwargs):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        error_result = ToolBase.wrap_error(e, error_code)
                        for k, v in default_fields.items():
                            error_result.setdefault(k, v)
                        return error_result
                return wrapper
        return decorator

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
