"""
HarmonyOS MCP Server 工具模块

按功能域组织的 MCP 工具函数。
使用 @mcp_tool 装饰器自动注册到全局注册表。
"""

from . import device
from . import build
from . import packages
from . import ui
from . import ui_tree
from . import logs
from . import compile
from . import registry

__all__ = [
    'device',
    'build', 
    'packages',
    'ui',
    'ui_tree',
    'logs',
    'compile',
    'registry',
]
