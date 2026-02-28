"""
HarmonyOS MCP Server 主入口

"""
from fastmcp import FastMCP
from loguru import logger

from .config import Config

server = FastMCP("harmonyos-tools")


def _register_tools():
    """
    自动注册所有工具

    工作原理：
    1. 导入各工具模块，触发模块中 @mcp_tool 装饰器的执行
    2. 装饰器将函数注册到 common/tools/registry.py 的全局注册表
    3. 遍历注册表，将所有工具注册到 FastMCP 服务器
    """
    from .tools import general, build, ui, ui_tree
    from .tools.log.query import logs_query
    from common.tools.registry import get_registered_tools, get_tool_summary

    for entry in get_registered_tools():
        server.tool()(entry.func)

    summary = get_tool_summary()
    logger.info(
        f"已注册 {summary['total']} 个 MCP 工具, "
        f"分类: {summary['categories']}"
    )


_register_tools()

mcp = server


def main():
    """MCP 服务器入口函数"""
    from .utils.logger import setup_logger

    setup_logger()

    Config.ensure_init()
    logger.info("HarmonyOS MCP Server 启动中...")

    from .container import get_hdc

    try:
        hdc = get_hdc()
        devices = hdc.list_devices()
        logger.info(f"检测到 {len(devices)} 个设备")
    except Exception as e:
        logger.warning(f"设备检测失败: {e}")

    mcp.run()


if __name__ == "__main__":
    main()
