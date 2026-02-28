"""
HarmonyOS MCP Server

AI-assisted HarmonyOS development tools via Model Context Protocol.
"""

__version__ = "0.3.0"
__author__ = "HarmonyOS MCP Team"

from .server import mcp, main
from .container import container, get_hdc, get_ui_operations, get_hilogtool, get_hvigor
from .config import Config, LogSecurityConfig
from common.exceptions import MCPError

__all__ = [
    "mcp",
    "main",
    "__version__",
    "container",
    "get_hdc",
    "get_ui_operations",
    "get_hilogtool",
    "get_hvigor",
    "Config",
    "LogSecurityConfig",
    "MCPError",
]
