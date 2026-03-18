"""
HarmonyOS MCP 依赖注入容器
"""
from common.container import Container

container = Container()


def _register_services():
    """注册所有服务"""
    from .utils.hdc import HdcWrapper
    from .utils.wrappers.ui_operations import UiTestWrapper
    from .utils.wrappers.hvigor_wrapper import HvigorWrapper
    from .utils.wrappers.hilogtool_wrapper import HilogtoolWrapper

    container.register(HdcWrapper, lambda: HdcWrapper())
    container.register(UiTestWrapper, lambda: UiTestWrapper(container.get(HdcWrapper)))
    container.register(HvigorWrapper, lambda: HvigorWrapper())
    container.register(HilogtoolWrapper, lambda: HilogtoolWrapper())


_registered = False


def _ensure_registered():
    global _registered
    if not _registered:
        _register_services()
        _registered = True


def get_hdc():
    from .utils.hdc import HdcWrapper
    _ensure_registered()
    return container.get(HdcWrapper)


def get_ui_operations():
    from .utils.wrappers.ui_operations import UiTestWrapper
    _ensure_registered()
    return container.get(UiTestWrapper)


def get_hilogtool():
    from .utils.wrappers.hilogtool_wrapper import HilogtoolWrapper
    _ensure_registered()
    return container.get(HilogtoolWrapper)


def get_hvigor():
    from .utils.wrappers.hvigor_wrapper import HvigorWrapper
    _ensure_registered()
    return container.get(HvigorWrapper)
