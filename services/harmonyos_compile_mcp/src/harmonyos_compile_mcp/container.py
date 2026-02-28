"""
依赖注入容器 - 编译工具专用

继承 common 的 _BaseContainer，
定义编译工具的具体服务创建逻辑。
"""
from loguru import logger

from common.container import _BaseContainer


class _Container(_BaseContainer):
    """
    编译工具依赖注入容器

    管理单例生命周期，支持：
    - 懒加载实例化
    - 测试时的 mock 注入
    - 服务依赖解析
    """

    def _create(self, service_type):
        """创建服务实例"""
        logger.debug(f"创建服务实例: {service_type.__name__}")

        # 检查是否有自定义工厂
        if service_type in self._factories:
            return self._factories[service_type]()

        # 延迟导入避免循环依赖
        from .utils.compile_wrapper import CompileLibraryManager

        if service_type == CompileLibraryManager:
            instance = CompileLibraryManager()
            logger.debug("CompileLibraryManager 初始化成功")
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


def get_compile_manager():
    """获取 CompileLibraryManager 实例"""
    from .utils.compile_wrapper import CompileLibraryManager

    return Container.get(CompileLibraryManager)
