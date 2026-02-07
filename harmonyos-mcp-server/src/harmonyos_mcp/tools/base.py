"""
工具基类

提供所有工具函数的公共方法，消除重复代码。
"""
from typing import Optional, Tuple, Union
from loguru import logger

from ..container import get_hdc
from ..exceptions import DeviceNotFoundError
from ..types import BaseResult


class ToolBase:
    """
    工具基类
    
    提供公共方法：
    - 设备 ID 获取和验证
    - 异常包装
    - 结果格式化
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
