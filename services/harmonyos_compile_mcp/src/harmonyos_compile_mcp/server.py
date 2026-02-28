"""
HarmonyOS MCP Server - 编译工具主入口
"""
from loguru import logger

from common.server.base import create_server, run_server
from .config import Config


def _setup_logger():
    from .utils.logger import setup_logger
    setup_logger()


# 导入工具模块触发注册
from .tools import compile_tools

# 创建服务器
mcp = create_server("harmonyos-compile-tools")


def main():
    run_server(
        mcp,
        config_class=Config,
        setup_logger_func=_setup_logger,
    )


if __name__ == "__main__":
    main()
