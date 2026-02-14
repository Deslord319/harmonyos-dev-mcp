"""
HarmonyOS MCP Server 主入口

重构后的精简版本，将业务逻辑拆分到 tools/ 模块中。
使用 tools/registry.py 的自动注册机制替代手动逐一注册。
"""
import sys
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
    from .tools import general, build, ui, ui_tree, logs, compile  # noqa: F401
    from .tools.registry import get_registered_tools, get_tool_summary

    # 从注册表自动注册到 FastMCP
    for entry in get_registered_tools():
        server.tool()(entry.func)

    summary = get_tool_summary()
    logger.info(
        f"已注册 {summary['total']} 个 MCP 工具, "
        f"分类: {summary['categories']}"
    )


# 注册工具
_register_tools()

# 导出 mcp 实例供 FastMCP 使用
mcp = server


def main():
    """MCP 服务器入口函数"""
    from .utils.logger import setup_logger
    
    # 设置日志（仅在实际运行服务时配置，测试时不触发）
    setup_logger()
    
    # 初始化配置
    Config.ensure_init()
    
    # 验证配置
    if not Config.validate():
        logger.error("配置验证失败,请检查环境变量")
        sys.exit(1)

    logger.info("HarmonyOS MCP Server 启动")
    logger.info(f"hdc路径: {Config.HDC_PATH}")

    # 启动MCP服务器（捕获退出信号）
    try:
        server.run()
    except KeyboardInterrupt:
        logger.info("收到退出信号，服务器关闭")
    except SystemExit:
        pass


if __name__ == "__main__":
    main()
