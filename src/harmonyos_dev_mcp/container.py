"""Dependency injection container for the dev service."""

from harmonyos_dev_mcp._common.container import Container

container = Container()


def _register_services():
    from .device.hdc import HdcWrapper
    from .utils.wrappers.hilogtool_wrapper import HilogtoolWrapper
    from .ui.operations import UiTestWrapper

    container.register(HdcWrapper, lambda: HdcWrapper())
    container.register(UiTestWrapper, lambda: UiTestWrapper(container.get(HdcWrapper)))
    container.register(HilogtoolWrapper, lambda: HilogtoolWrapper())


_registered = False


def _ensure_registered():
    global _registered
    if not _registered:
        _register_services()
        _registered = True


def _set_registered(value: bool) -> None:
    """Test-only hook to set the module-level registration flag.

    ``import harmonyos_dev_mcp.container as m`` resolves to the ``container``
    singleton: the package ``__init__`` re-exports that instance under the same
    name, shadowing the submodule reference. Assigning ``m._registered`` would
    therefore mutate the instance, not the module global that
    ``_ensure_registered`` reads. Tests must flip the real flag through here so
    mock factories registered into the container are not overwritten by a
    later ``_register_services`` call.
    """
    global _registered
    _registered = value


def get_hdc():
    from .device.hdc import HdcWrapper

    _ensure_registered()
    return container.get(HdcWrapper)


def get_ui_operations():
    from .ui.operations import UiTestWrapper

    _ensure_registered()
    return container.get(UiTestWrapper)


def get_hilogtool():
    from .utils.wrappers.hilogtool_wrapper import HilogtoolWrapper

    _ensure_registered()
    return container.get(HilogtoolWrapper)
