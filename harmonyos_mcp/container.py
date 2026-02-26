"""
依赖注入容器

管理服务实例的生命周期，支持单例模式和测试时的 mock 注入。
使用实例级状态，避免类级别可变属性的 Python 反模式。
"""
from typing import TypeVar, Type, Dict, Any, Callable
from loguru import logger

T = TypeVar('T')


class _Container:
    """
    依赖注入容器
    
    管理单例生命周期，支持：
    - 懒加载实例化
    - 测试时的 mock 注入
    - 服务依赖解析
    - 多容器实例（未来多设备支持）
    
    Usage:
        # 通过模块级便捷函数获取服务
        hdc = get_hdc()
        
        # 测试时注入 mock（通过默认容器）
        from harmonyos_mcp.container import Container
        Container.register(HdcWrapper, mock_hdc)
        
        # 重置容器（测试清理）
        Container.reset()
    """
    
    def __init__(self):
        self._instances: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable] = {}
    
    def get(self, service_type: Type[T]) -> T:
        """
        获取服务实例（单例模式）
        
        Args:
            service_type: 服务类型
            
        Returns:
            服务实例
        """
        if service_type not in self._instances:
            self._instances[service_type] = self._create(service_type)
        return self._instances[service_type]
    
    def _create(self, service_type: Type[T]) -> T:
        """
        创建服务实例
        
        Args:
            service_type: 服务类型
            
        Returns:
            新创建的服务实例
        """
        logger.debug(f"创建服务实例: {service_type.__name__}")
        
        # 检查是否有自定义工厂
        if service_type in self._factories:
            return self._factories[service_type]()
        
        # 延迟导入避免循环依赖
        from .utils.hdc import HdcWrapper
        from .utils.wrappers.compile_wrapper import CompileLibraryManager
        from .utils.wrappers.ui_operations import UiTestWrapper
        from .utils.wrappers.hvigor_wrapper import HvigorWrapper
        from .utils.wrappers.hilogtool_wrapper import HilogtoolWrapper
        
        if service_type == HdcWrapper:
            instance = HdcWrapper()
            logger.debug("HdcWrapper 初始化成功")
            return instance
            
        elif service_type == CompileLibraryManager:
            instance = CompileLibraryManager()
            logger.debug("CompileLibraryManager 初始化成功")
            return instance
            
        elif service_type == UiTestWrapper:
            # UiTestWrapper 依赖 HdcWrapper
            hdc = self.get(HdcWrapper)
            instance = UiTestWrapper(hdc)
            logger.debug("UiTestWrapper 初始化成功")
            return instance
            
        elif service_type == HilogtoolWrapper:
            instance = HilogtoolWrapper()
            logger.debug("HilogtoolWrapper 初始化成功")
            return instance
            
        elif service_type == HvigorWrapper:
            instance = HvigorWrapper()
            logger.debug("HvigorWrapper 初始化成功")
            return instance
            
        else:
            raise ValueError(f"未知的服务类型: {service_type.__name__}")
    
    def register(self, service_type: Type[T], instance: T) -> None:
        """
        手动注册实例（用于测试 mock）
        
        Args:
            service_type: 服务类型
            instance: 服务实例
        """
        logger.debug(f"手动注册服务实例: {service_type.__name__}")
        self._instances[service_type] = instance
    
    def reset(self) -> None:
        """
        重置容器（用于测试清理）
        
        清除所有已创建的实例和注册的工厂。
        """
        logger.debug("重置依赖注入容器")
        self._instances.clear()
        self._factories.clear()


# ============================================================================
# 模块级默认容器（单例）
# ============================================================================

Container = _Container()
"""默认的全局容器实例，所有便捷函数和测试 mock 注入都通过此实例操作。

如需创建独立容器（如测试隔离），可使用 _Container() 构造新实例。
"""


# ============================================================================
# 便捷访问函数
# ============================================================================

def get_hdc():
    """获取 HdcWrapper 实例"""
    from .utils.hdc import HdcWrapper
    return Container.get(HdcWrapper)


def get_compile_manager():
    """获取 CompileLibraryManager 实例"""
    from .utils.wrappers.compile_wrapper import CompileLibraryManager
    return Container.get(CompileLibraryManager)


def get_ui_operations():
    """获取 UiTestWrapper 实例"""
    from .utils.wrappers.ui_operations import UiTestWrapper
    return Container.get(UiTestWrapper)


def get_hilogtool():
    """获取 HilogtoolWrapper 实例"""
    from .utils.wrappers.hilogtool_wrapper import HilogtoolWrapper
    return Container.get(HilogtoolWrapper)
