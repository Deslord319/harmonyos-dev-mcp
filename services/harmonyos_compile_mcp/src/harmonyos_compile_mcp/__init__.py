"""
HarmonyOS MCP Server - 编译工具
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("harmonyos-compile-mcp")
except PackageNotFoundError:
    __version__ = "0.7.0"

__author__ = "HarmonyOS MCP Team"

from .server import mcp, main

__all__ = [
    "mcp",
    "main",
    "__version__",
]
