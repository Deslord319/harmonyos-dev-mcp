"""
HarmonyOS MCP Server

AI-assisted HarmonyOS development tools via Model Context Protocol.

架构：
- server.py: MCP 服务器入口
- container.py: 依赖注入容器
- tools/: 按功能域拆分的 MCP 工具（全部异步化）
- utils/: 底层封装（hdc/wrappers/通用工具）
- types.py: TypedDict 类型定义（按需导入：from harmonyos_mcp.types import ...）
"""

__version__ = "0.3.0"
__author__ = "HarmonyOS MCP Team"

# 主入口
from .server import mcp, main

# 依赖注入
from .container import Container, get_hdc, get_ui_operations, get_hilogtool

# 异常（从 common 导入）
from common.exceptions import (
    HarmonyOSMCPError,
    DeviceError,
    CommandError,
    BuildError,
    UIError,
)

# 配置
from .config import Config, LogSecurityConfig

__all__ = [
    # 主入口
    "mcp",
    "main",
    "__version__",
    # 依赖注入
    "Container",
    "get_hdc",
    "get_ui_operations",
    "get_hilogtool",
    # 配置
    "Config",
    "LogSecurityConfig",
    # 异常
    "HarmonyOSMCPError",
    "DeviceError",
    "CommandError",
    "BuildError",
    "UIError",
]
