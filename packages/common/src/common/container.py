"""
依赖注入容器基类

提供通用的单例管理、mock 注入和容器清理功能。
具体的服务创建逻辑由子类 override _create() 实现。
"""
from typing import TypeVar, Type, Dict, Any, Callable
from loguru import logger

T = TypeVar('T')


class _BaseContainer:
    """
    依赖注入容器基类

    管理单例生命周期，支持：
    - 懒加载实例化
    - 测试时的 mock 注入
    - 服务依赖解析

    子类必须 override _create() 方法来定义具体服务的创建逻辑。

    Usage:
        class _MyContainer(_BaseContainer):
            def _create(self, service_type):
                if service_type == MyService:
                    return MyService()
                raise ValueError(f"未知的服务类型: {service_type.__name__}")

        Container = _MyContainer()
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
        创建服务实例（子类 override）

        Args:
            service_type: 服务类型

        Returns:
            新创建的服务实例
        """
        logger.debug(f"创建服务实例: {service_type.__name__}")

        # 检查是否有自定义工厂
        if service_type in self._factories:
            return self._factories[service_type]()

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
