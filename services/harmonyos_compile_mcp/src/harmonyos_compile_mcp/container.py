"""
HarmonyOS Compile MCP 依赖注入容器
"""
from common.container import Container

container = Container()


def _register_services():
    """注册所有服务"""
    from .utils.compile_wrapper import CompileLibraryManager

    container.register(CompileLibraryManager, lambda: CompileLibraryManager())


_registered = False


def _ensure_registered():
    global _registered
    if not _registered:
        _register_services()
        _registered = True


def get_compile_manager():
    from .utils.compile_wrapper import CompileLibraryManager
    _ensure_registered()
    return container.get(CompileLibraryManager)
