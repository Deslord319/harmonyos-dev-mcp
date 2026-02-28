"""
HarmonyOS MCP Server 主入口
"""
from loguru import logger

from common.server.base import create_server, run_server
from .config import Config


def _setup_logger():
    from .utils.logger import setup_logger
    setup_logger()


def _on_startup():
    from .container import get_hdc
    try:
        hdc = get_hdc()
        devices = hdc.list_devices()
        logger.info(f"检测到 {len(devices)} 个设备")
    except Exception as e:
        logger.warning(f"设备检测失败: {e}")


# 导入工具模块触发注册
from .tools import general, build, ui, ui_tree
from .tools.log.query import logs_query

# 创建服务器
mcp = create_server("harmonyos-tools")


def main():
    run_server(
        mcp,
        config_class=Config,
        setup_logger_func=_setup_logger,
        on_startup=_on_startup,
    )


if __name__ == "__main__":
    main()
