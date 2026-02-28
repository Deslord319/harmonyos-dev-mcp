"""
依赖注入容器

使用注册模式管理单例生命周期。
"""
from typing import TypeVar, Type, Dict, Any, Callable
from loguru import logger

T = TypeVar('T')


class Container:
    """
    依赖注入容器

    使用注册模式，服务通过 register() 注册工厂函数。

    Usage:
        container = Container()
        container.register(HdcWrapper, lambda: HdcWrapper())
        hdc = container.get(HdcWrapper)
    """

    def __init__(self):
        self._instances: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable] = {}

    def register(self, service_type: Type[T], factory: Callable[[], T]) -> None:
        self._factories[service_type] = factory
        logger.debug(f"注册服务工厂: {service_type.__name__}")

    def get(self, service_type: Type[T]) -> T:
        if service_type not in self._instances:
            if service_type not in self._factories:
                raise ValueError(f"未注册的服务类型: {service_type.__name__}")
            self._instances[service_type] = self._factories[service_type]()
            logger.debug(f"创建服务实例: {service_type.__name__}")
        return self._instances[service_type]

    def reset(self) -> None:
        self._instances.clear()
        self._factories.clear()
        logger.debug("容器已重置")
