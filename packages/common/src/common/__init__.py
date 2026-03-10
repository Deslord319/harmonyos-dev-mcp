"""
HarmonyOS MCP Common Package

提供公共基础设施：
- Container: 依赖注入容器
- MCPError: 异常基类
- BaseResult: 返回类型基类
- ConfigBase: 配置基类
- create_server/run_server: MCP服务器工厂
"""

__version__ = "0.6.0"
__author__ = "HarmonyOS MCP Team"

from .container import Container
from .exceptions import MCPError
from .types import BaseResult
from .config.base import ConfigBase
from .server.base import create_server, run_server

__all__ = [
    "Container",
    "MCPError",
    "BaseResult",
    "ConfigBase",
    "create_server",
    "run_server",
]
