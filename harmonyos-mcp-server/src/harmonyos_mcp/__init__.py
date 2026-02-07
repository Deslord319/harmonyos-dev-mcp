"""
HarmonyOS MCP Server

AI-assisted HarmonyOS development tools via Model Context Protocol.

重构版本：
- tools/: 按功能域拆分的工具模块
- container.py: 依赖注入容器
- types.py: 类型定义
- exceptions.py: 异常定义
"""

__version__ = "0.2.0"
__author__ = "HarmonyOS MCP Team"

# 保持向后兼容
from .server import mcp, main

# 新增导出
from .container import Container, get_hdc, get_compile_manager, get_ui_operations
from .exceptions import (
    HarmonyOSMCPError,
    DeviceNotFoundError,
    DeviceConnectionError,
    CommandTimeoutError,
    BuildFailedError,
    AppNotFoundError,
    ElementNotFoundError,
)

__all__ = [
    # 主入口
    "mcp",
    "main",
    "__version__",
    # 容器
    "Container",
    "get_hdc",
    "get_compile_manager", 
    "get_ui_operations",
    # 异常
    "HarmonyOSMCPError",
    "DeviceNotFoundError",
    "DeviceConnectionError",
    "CommandTimeoutError",
    "BuildFailedError",
    "AppNotFoundError",
    "ElementNotFoundError",
]

