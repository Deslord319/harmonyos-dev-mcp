"""
HarmonyOS MCP Server 主入口

重构后的精简版本，将业务逻辑拆分到 tools/ 模块中。
原始版本备份: server_backup.py
"""
import sys
from fastmcp import FastMCP
from loguru import logger

from .config import Config
from .utils.logger import setup_logger

# 设置日志
setup_logger()

# 创建MCP服务器
server = FastMCP("harmonyos-tools")


def _register_tools():
    """
    注册所有工具
    
    从各功能模块导入工具函数并注册到 MCP 服务器。
    """
    from .tools import device, build, packages, ui, ui_tree, logs, compile

    # ========================================================================
    # 设备管理工具
    # ========================================================================
    server.tool()(device.list_devices)
    server.tool()(device.hilog_receive)

    # ========================================================================
    # 构建部署工具
    # ========================================================================
    server.tool()(build.build_app)
    server.tool()(build.install_app)
    server.tool()(build.run_app)
    server.tool()(build.uninstall_app)

    # ========================================================================
    # 包管理工具
    # ========================================================================
    server.tool()(packages.list_packages)
    server.tool()(packages.get_package_abilities)
    server.tool()(packages.get_main_ability)

    # ========================================================================
    # UI 树工具
    # ========================================================================
    server.tool()(ui_tree.get_ui_tree)
    server.tool()(ui_tree.list_windows)

    # ========================================================================
    # UI 操作工具
    # ========================================================================
    server.tool()(ui.click_element)
    server.tool()(ui.long_press_element)
    server.tool()(ui.swipe)
    server.tool()(ui.input_text)
    server.tool()(ui.press_key)
    server.tool()(ui.find_element)

    # ========================================================================
    # 日志分析工具
    # ========================================================================
    server.tool()(logs.logs_fetch)
    server.tool()(logs.logs_save_snapshot)
    server.tool()(logs.logs_analyze)

    # ========================================================================
    # 三方库编译工具
    # ========================================================================
    server.tool()(compile.check_wsl)
    server.tool()(compile.check_harmonyos_compiler_tools)
    server.tool()(compile.clone_library)
    server.tool()(compile.analyze_build_system)
    server.tool()(compile.read_build_files)
    server.tool()(compile.write_compile_script)
    server.tool()(compile.execute_compile_script)
    server.tool()(compile.verify_so_output)

    logger.info("已注册 28 个 MCP 工具")


# 注册工具
_register_tools()

# 导出 mcp 实例供 FastMCP 使用
mcp = server


def main():
    """MCP 服务器入口函数"""
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
