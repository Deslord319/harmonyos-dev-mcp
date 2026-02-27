"""
HarmonyOS MCP Server 主入口

"""

from fastmcp import FastMCP
from loguru import logger

from .config import Config

# 创建MCP服务器
server = FastMCP("harmonyos-tools")


def _register_tools():
    """
    自动注册所有工具

    工作原理：
    1. 导入各工具模块，触发模块中 @mcp_tool 装饰器的执行
    2. 装饰器将函数注册到 tools/registry.py 的全局注册表
    3. 遍历注册表，将所有工具注册到 FastMCP 服务器
    """
    # 导入工具模块（触发 @mcp_tool 装饰器注册）
    from .tools import general, build, ui, ui_tree
    from .tools.log.query import logs_query
    from .tools.registry import get_registered_tools, get_tool_summary

    # 从注册表自动注册到 FastMCP
    for entry in get_registered_tools():
        server.tool()(entry.func)

    summary = get_tool_summary()
    logger.info(f"已注册 {summary['total']} 个 MCP 工具, 分类: {summary['categories']}")


# 注册工具
_register_tools()

# 导出 mcp 实例供 FastMCP 使用
mcp = server


def main():
    """MCP 服务器入口函数"""
    from .utils.logger import setup_logger

    # 设置日志（仅在实际运行服务时配置，测试时不触发）
    setup_logger()

    Config.ensure_init()
    logger.info("HarmonyOS MCP Server 启动中...")

    # 验证 hdc 可用
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
