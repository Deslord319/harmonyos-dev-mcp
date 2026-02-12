"""
HarmonyOS MCP Server 工具模块

按功能域组织的 MCP 工具函数（全部异步化）。
使用 @mcp_tool 装饰器自动注册到全局注册表。

模块列表：
- device: 设备管理（list_devices, hilog_receive）
- build: 构建部署（build_app, install_app, run_app, uninstall_app）
- packages: 包管理（list_packages, get_package_abilities, get_main_ability）
- ui: UI 操作（click_element, long_press_element, swipe, input_text, press_key, find_element）
- ui_tree: UI 树（get_ui_tree, list_windows）
- logs: 日志分析（logs_fetch, logs_save_snapshot, logs_analyze）
- compile: 三方库编译（check_wsl, check_harmonyos_compiler_tools, clone_library, ...）
"""

from . import device
from . import build
from . import packages
from . import ui
from . import ui_tree
from . import logs
from . import compile
from . import registry
from .registry import get_registered_tools, get_tool_summary
from .base import ToolBase

__all__ = [
    'device',
    'build',
    'packages',
    'ui',
    'ui_tree',
    'logs',
    'compile',
    'registry',
    'get_registered_tools',
    'get_tool_summary',
    'ToolBase',
]
