"""
HarmonyOS MCP Server - 编译工具主入口
"""

from fastmcp import FastMCP
from loguru import logger

from .config import Config

# 创建MCP服务器
server = FastMCP("harmonyos-compile-tools")


def _register_tools():
    """
    自动注册所有编译工具
    """
    # 导入工具模块（触发 @mcp_tool 装饰器注册）
    from .tools import compile_tools
    from common.tools.registry import get_registered_tools, get_tool_summary

    # 从注册表自动注册到 FastMCP
    for entry in get_registered_tools():
        server.tool()(entry.func)

    summary = get_tool_summary()
    logger.info(f"已注册 {summary['total']} 个编译工具, 分类: {summary['categories']}")


# 注册工具
_register_tools()

# 导出 mcp 实例供 FastMCP 使用
mcp = server


def main():
    """MCP 服务器入口函数"""
    from .utils.logger import setup_logger

    # 设置日志
    setup_logger()

    Config.ensure_init()
    logger.info("HarmonyOS MCP 编译工具服务器启动中...")

    mcp.run()


if __name__ == "__main__":
    main()
