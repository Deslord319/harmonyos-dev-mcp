"""
依赖注入容器

管理服务实例的生命周期，支持单例模式和测试时的 mock 注入。
"""
from typing import TypeVar, Type, Dict, Optional, Any
from loguru import logger

T = TypeVar('T')


class Container:
    """
    依赖注入容器
    
    管理单例生命周期，支持：
    - 懒加载实例化
    - 测试时的 mock 注入
    - 服务依赖解析
    
    Usage:
        # 获取服务实例
        hdc = Container.get(HdcWrapper)
        
        # 测试时注入 mock
        Container.register(HdcWrapper, mock_hdc)
        
        # 重置容器（测试清理）
        Container.reset()
    """
    
    _instances: Dict[Type, Any] = {}
    _factories: Dict[Type, callable] = {}
    
    @classmethod
    def get(cls, service_type: Type[T]) -> T:
        """
        获取服务实例（单例模式）
        
        Args:
            service_type: 服务类型
            
        Returns:
            服务实例
        """
        if service_type not in cls._instances:
            cls._instances[service_type] = cls._create(service_type)
        return cls._instances[service_type]
    
    @classmethod
    def _create(cls, service_type: Type[T]) -> T:
        """
        创建服务实例
        
        Args:
            service_type: 服务类型
            
        Returns:
            新创建的服务实例
        """
        logger.debug(f"创建服务实例: {service_type.__name__}")
        
        # 检查是否有自定义工厂
        if service_type in cls._factories:
            return cls._factories[service_type]()
        
        # 延迟导入避免循环依赖
        from .utils.hdc_wrapper import HdcWrapper
        from .utils.compile_wrapper import CompileLibraryManager
        from .utils.ui_operations import UIOperations
        from .utils.hvigor_wrapper import HvigorWrapper
        
        if service_type == HdcWrapper:
            instance = HdcWrapper()
            logger.info("HdcWrapper 初始化成功")
            return instance
            
        elif service_type == CompileLibraryManager:
            instance = CompileLibraryManager()
            logger.info("CompileLibraryManager 初始化成功")
            return instance
            
        elif service_type == UIOperations:
            # UIOperations 依赖 HdcWrapper
            hdc = cls.get(HdcWrapper)
            instance = UIOperations(hdc)
            logger.info("UIOperations 初始化成功")
            return instance
            
        else:
            raise ValueError(f"未知的服务类型: {service_type.__name__}")
    
    @classmethod
    def register(cls, service_type: Type[T], instance: T) -> None:
        """
        手动注册实例（用于测试 mock）
        
        Args:
            service_type: 服务类型
            instance: 服务实例
        """
        logger.debug(f"手动注册服务实例: {service_type.__name__}")
        cls._instances[service_type] = instance
    
    @classmethod
    def register_factory(cls, service_type: Type[T], factory: callable) -> None:
        """
        注册服务工厂函数
        
        Args:
            service_type: 服务类型
            factory: 工厂函数，无参数，返回服务实例
        """
        cls._factories[service_type] = factory
    
    @classmethod
    def reset(cls) -> None:
        """
        重置容器（用于测试清理）
        
        清除所有已创建的实例和注册的工厂。
        """
        logger.debug("重置依赖注入容器")
        cls._instances.clear()
        cls._factories.clear()
    
    @classmethod
    def has(cls, service_type: Type) -> bool:
        """
        检查是否已有实例
        
        Args:
            service_type: 服务类型
            
        Returns:
            是否存在实例
        """
        return service_type in cls._instances
    
    @classmethod
    def remove(cls, service_type: Type) -> None:
        """
        移除指定服务实例
        
        Args:
            service_type: 服务类型
        """
        if service_type in cls._instances:
            del cls._instances[service_type]
            logger.debug(f"移除服务实例: {service_type.__name__}")


# ============================================================================
# 便捷访问函数
# ============================================================================

def get_hdc():
    """获取 HdcWrapper 实例"""
    from .utils.hdc_wrapper import HdcWrapper
    return Container.get(HdcWrapper)


def get_compile_manager():
    """获取 CompileLibraryManager 实例"""
    from .utils.compile_wrapper import CompileLibraryManager
    return Container.get(CompileLibraryManager)


def get_ui_operations():
    """获取 UIOperations 实例"""
    from .utils.ui_operations import UIOperations
    return Container.get(UIOperations)
