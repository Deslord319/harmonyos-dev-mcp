"""Dependency injection container for the dev service."""

from common.container import Container

container = Container()


def _register_services():
    from .utils.hdc import HdcWrapper
    from .utils.wrappers.hilogtool_wrapper import HilogtoolWrapper
    from .utils.wrappers.ui_operations import UiTestWrapper

    container.register(HdcWrapper, lambda: HdcWrapper())
    container.register(UiTestWrapper, lambda: UiTestWrapper(container.get(HdcWrapper)))
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
