"""
HarmonyOS MCP Server - 编译工具
"""

__version__ = "0.6.0"
__author__ = "HarmonyOS MCP Team"

from .server import mcp, main

__all__ = [
    "mcp",
    "main",
    "__version__",
]
