"""
HarmonyOS MCP Server

AI-assisted HarmonyOS development tools via Model Context Protocol.
"""

__version__ = "0.1.0"
__author__ = "HarmonyOS MCP Team"

from .server import mcp, main

__all__ = ["mcp", "main", "__version__"]

