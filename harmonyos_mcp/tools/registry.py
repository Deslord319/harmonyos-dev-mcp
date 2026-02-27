"""
MCP 工具自动注册机制（re-export from common）

保持向后兼容：所有从此模块导入的符号实际来自 common。
"""
from common.tools.registry import (
    mcp_tool,
    ToolEntry,
    get_registered_tools,
    get_tools_by_category,
    get_tool_summary,
    clear_registry,
)

__all__ = [
    "mcp_tool",
    "ToolEntry",
    "get_registered_tools",
    "get_tools_by_category",
    "get_tool_summary",
    "clear_registry",
]
