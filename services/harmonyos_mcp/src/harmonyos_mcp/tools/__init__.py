"""
HarmonyOS MCP Server 工具模块

按功能域组织的 MCP 工具函数（全部异步化）。
使用 @mcp_tool 装饰器自动注册到全局注册表。
"""

from common.tools.registry import get_registered_tools, get_tool_summary, mcp_tool
from common.tools.base import ToolBase

__all__ = [
    'get_registered_tools',
    'get_tool_summary',
    'mcp_tool',
    'ToolBase',
]
