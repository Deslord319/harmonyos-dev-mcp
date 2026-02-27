"""
HarmonyOS MCP Server 工具模块

按功能域组织的 MCP 工具函数（全部异步化）。
使用 @mcp_toolkit 装饰器自动注册到全局注册表。

模块列表（五大分类）：

一、通用:
- general: 设备管理+包管理（list_devices, list_packages, get_package_abilities, get_main_ability）

二、鸿蒙日志分析:
- logs: 日志工具（hilog_receive, logs_fetch, logs_save_snapshot, logs_analyze）

三、鸿蒙打包编译:
- build: 构建部署（build_app, install_app, run_app, uninstall_app）

四、UI 测试:
- ui_tree: UI 树（get_ui_tree, list_windows）
- ui: UI 操作（click_element, long_press_element, swipe, input_text, press_key, find_element, screenshot, screenshot_element）

五、三方库编译:
- compile: 三方库编译（check_wsl, check_harmonyos_compiler_tools, clone_library, ...）

注意：各工具模块由 server.py._register_tools() 显式导入触发注册，
此 __init__.py 仅导出 registry 接口和 ToolBase，不急切加载工具模块。
"""

from .registry import get_registered_tools, get_tool_summary
from .base import ToolBase
from . import log as logs

__all__ = [
    "get_registered_tools",
    "get_tool_summary",
    "ToolBase",
    "logs",
]
