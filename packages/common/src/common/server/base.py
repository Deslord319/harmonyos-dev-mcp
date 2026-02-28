"""
MCP 服务器工厂

统一的 MCP 服务器创建和工具注册。
"""
from typing import List, Optional, Callable
from fastmcp import FastMCP
from loguru import logger

from common.tools.registry import get_registered_tools, get_tool_summary


def create_server(
    name: str,
    tool_modules: Optional[List] = None,
) -> FastMCP:
    """
    创建 MCP 服务器

    Args:
        name: 服务器名称
        tool_modules: 要导入的工具模块列表（用于触发 @mcp_tool 注册）

    Returns:
        FastMCP 服务器实例
    """
    server = FastMCP(name)

    if tool_modules:
        for module in tool_modules:
                pass

    for entry in get_registered_tools():
        server.tool()(entry.func)

    summary = get_tool_summary()
    logger.info(f"已注册 {summary['total']} 个工具, 分类: {summary['categories']}")

    return server


def run_server(
    server: FastMCP,
    config_class=None,
    setup_logger_func: Optional[Callable] = None,
    on_startup: Optional[Callable] = None,
):
    """
    运行 MCP 服务器

    Args:
        server: FastMCP 服务器实例
        config_class: 配置类（会调用 ensure_init）
        setup_logger_func: 日志设置函数
        on_startup: 启动回调
    """
    if setup_logger_func:
        setup_logger_func()

    if config_class:
        config_class.ensure_init()

    if on_startup:
        try:
            on_startup()
        except Exception as e:
            logger.warning(f"启动回调失败: {e}")

    server.run()
