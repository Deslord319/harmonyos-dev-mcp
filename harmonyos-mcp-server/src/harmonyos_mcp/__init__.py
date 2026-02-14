"""
HarmonyOS MCP Server

AI-assisted HarmonyOS development tools via Model Context Protocol.

重构版本：
- tools/: 按功能域拆分的工具模块（全部异步化）
- container.py: 依赖注入容器
- types.py: 类型定义
- exceptions.py: 异常定义
- utils/hdc_wrapper.py: 命令白名单安全校验
"""

__version__ = "0.3.0"
__author__ = "HarmonyOS MCP Team"

# 保持向后兼容
from .server import mcp, main

# 容器
from .container import Container, get_hdc, get_compile_manager, get_ui_operations, get_hilogtool, get_hvigor

# 异常
from .exceptions import (
    HarmonyOSMCPError,
    DeviceNotFoundError,
    DeviceConnectionError,
    CommandTimeoutError,
    BuildFailedError,
    AppNotFoundError,
    ElementNotFoundError,
)

# 配置
from .config import Config, LogSecurityConfig

# 类型
from .types import (
    BaseResult,
    DeviceResult,
    ListDevicesResult,
    HilogReceiveResult,
    ScreenshotResult,
    ElementScreenshotResult,
    BuildResult,
    InstallResult,
    RunAppResult,
    UninstallResult,
    ListPackagesResult,
    PackageAbilitiesResult,
    MainAbilityResult,
    FindElementResult,
    UITreeResult,
    ListWindowsResult,
    LogsFetchResult,
    LogsSaveResult,
    LogsAnalyzeResult,
    WslCheckResult,
    CompilerToolsResult,
    CloneLibraryResult,
    AnalyzeBuildResult,
    ReadBuildFilesResult,
    WriteScriptResult,
    ExecuteScriptResult,
    VerifyOutputResult,
)

__all__ = [
    # 主入口
    "mcp",
    "main",
    "__version__",
    # 容器
    "Container",
    "get_hdc",
    "get_compile_manager",
    "get_ui_operations",
    "get_hilogtool",
    "get_hvigor",
    # 配置
    "Config",
    "LogSecurityConfig",
    # 异常
    "HarmonyOSMCPError",
    "DeviceNotFoundError",
    "DeviceConnectionError",
    "CommandTimeoutError",
    "BuildFailedError",
    "AppNotFoundError",
    "ElementNotFoundError",
    # 类型
    "BaseResult",
    "DeviceResult",
    "ListDevicesResult",
    "HilogReceiveResult",
    "ScreenshotResult",
    "ElementScreenshotResult",
    "BuildResult",
    "InstallResult",
    "RunAppResult",
    "UninstallResult",
    "ListPackagesResult",
    "PackageAbilitiesResult",
    "MainAbilityResult",
    "FindElementResult",
    "UITreeResult",
    "ListWindowsResult",
    "LogsFetchResult",
    "LogsSaveResult",
    "LogsAnalyzeResult",
    "WslCheckResult",
    "CompilerToolsResult",
    "CloneLibraryResult",
    "AnalyzeBuildResult",
    "ReadBuildFilesResult",
    "WriteScriptResult",
    "ExecuteScriptResult",
    "VerifyOutputResult",
]
