"""
依赖注入容器

继承 common 的 _BaseContainer，
定义 harmonyos_mcp 的具体服务创建逻辑。
"""
from loguru import logger

from common.container import _BaseContainer


class _Container(_BaseContainer):
    """
    HarmonyOS MCP 依赖注入容器

    管理单例生命周期，支持：
    - 懒加载实例化
    - 测试时的 mock 注入
    - 服务依赖解析

    Usage:
        # 通过模块级便捷函数获取服务
        hdc = get_hdc()

        # 测试时注入 mock（通过默认容器）
        from harmonyos_mcp.container import Container
        Container.register(HdcWrapper, mock_hdc)

        # 重置容器（测试清理）
        Container.reset()
    """

    def _create(self, service_type):
        """创建服务实例"""
        logger.debug(f"创建服务实例: {service_type.__name__}")

        # 检查是否有自定义工厂
        if service_type in self._factories:
            return self._factories[service_type]()

        # 延迟导入避免循环依赖
        from .utils.hdc import HdcWrapper
        from .utils.wrappers.ui_operations import UiTestWrapper
        from .utils.wrappers.hvigor_wrapper import HvigorWrapper
        from .utils.wrappers.hilogtool_wrapper import HilogtoolWrapper

        if service_type == HdcWrapper:
            instance = HdcWrapper()
            logger.debug("HdcWrapper 初始化成功")
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


def get_ui_operations():
    """获取 UiTestWrapper 实例"""
    from .utils.wrappers.ui_operations import UiTestWrapper
    return Container.get(UiTestWrapper)


def get_hilogtool():
    """获取 HilogtoolWrapper 实例"""
    from .utils.wrappers.hilogtool_wrapper import HilogtoolWrapper
    return Container.get(HilogtoolWrapper)
