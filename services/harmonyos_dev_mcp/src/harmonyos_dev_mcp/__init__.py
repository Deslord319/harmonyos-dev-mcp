"""HarmonyOS Dev MCP service package."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("harmonyos-dev-mcp")
except PackageNotFoundError:
    __version__ = "0.7.3"

__author__ = "HarmonyOS MCP Team"

from common.exceptions import MCPError

from .config import Config, LogSecurityConfig
from .container import container, get_hdc, get_hilogtool, get_ui_operations
from .server import main, mcp

__all__ = [
    "mcp",
    "main",
    "__version__",
    "container",
    "get_hdc",
    "get_ui_operations",
    "get_hilogtool",
    "Config",
    "LogSecurityConfig",
    "MCPError",
]
