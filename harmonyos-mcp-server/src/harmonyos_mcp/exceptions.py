"""
异常定义模块

定义所有自定义异常类，提供统一的错误处理机制。
"""


class HarmonyOSMCPError(Exception):
    """HarmonyOS MCP Server 基础异常"""
    
    def __init__(self, message: str, code: str = None):
        super().__init__(message)
        self.message = message
        self.code = code or "UNKNOWN_ERROR"
    
    def to_dict(self) -> dict:
        """转换为字典格式（用于 API 响应）"""
        return {
            'success': False,
            'error': self.message,
            'error_code': self.code
        }


# ============================================================================
# 设备相关异常
# ============================================================================

class DeviceError(HarmonyOSMCPError):
    """设备相关异常基类"""
    pass


class DeviceNotFoundError(DeviceError):
    """没有找到连接的设备"""
    
    def __init__(self, message: str = "没有找到连接的设备"):
        super().__init__(message, "DEVICE_NOT_FOUND")


class DeviceConnectionError(DeviceError):
    """设备连接错误"""
    
    def __init__(self, device_id: str, message: str = None):
        self.device_id = device_id
        msg = message or f"设备 {device_id} 连接失败"
        super().__init__(msg, "DEVICE_CONNECTION_ERROR")


class DeviceOfflineError(DeviceError):
    """设备离线"""
    
    def __init__(self, device_id: str):
        self.device_id = device_id
        super().__init__(f"设备 {device_id} 已离线", "DEVICE_OFFLINE")


# ============================================================================
# 命令执行异常
# ============================================================================

class CommandError(HarmonyOSMCPError):
    """命令执行异常基类"""
    pass


class CommandTimeoutError(CommandError):
    """命令执行超时"""
    
    def __init__(self, command: str, timeout: int):
        self.command = command
        self.timeout = timeout
        super().__init__(
            f"命令执行超时({timeout}秒): {command[:50]}...",
            "COMMAND_TIMEOUT"
        )


class CommandExecutionError(CommandError):
    """命令执行失败"""
    
    def __init__(self, command: str, returncode: int, stderr: str = None):
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        msg = f"命令执行失败(返回码 {returncode})"
        if stderr:
            msg += f": {stderr[:100]}"
        super().__init__(msg, "COMMAND_EXECUTION_ERROR")


# ============================================================================
# 构建相关异常
# ============================================================================

class BuildError(HarmonyOSMCPError):
    """构建相关异常基类"""
    pass


class ProjectNotFoundError(BuildError):
    """项目不存在"""
    
    def __init__(self, project_path: str):
        self.project_path = project_path
        super().__init__(f"项目不存在: {project_path}", "PROJECT_NOT_FOUND")


class BuildFailedError(BuildError):
    """构建失败"""
    
    def __init__(self, project_path: str, reason: str = None):
        self.project_path = project_path
        self.reason = reason
        msg = f"项目构建失败: {project_path}"
        if reason:
            msg += f" - {reason}"
        super().__init__(msg, "BUILD_FAILED")


class HvigorNotFoundError(BuildError):
    """hvigor 工具不存在"""
    
    def __init__(self):
        super().__init__(
            "未找到 hvigor 构建工具，请检查 DevEco Studio 安装",
            "HVIGOR_NOT_FOUND"
        )


# ============================================================================
# 应用相关异常
# ============================================================================

class AppError(HarmonyOSMCPError):
    """应用相关异常基类"""
    pass


class AppNotFoundError(AppError):
    """应用不存在"""
    
    def __init__(self, bundle_name: str):
        self.bundle_name = bundle_name
        super().__init__(f"应用不存在: {bundle_name}", "APP_NOT_FOUND")


class AppInstallError(AppError):
    """应用安装失败"""
    
    def __init__(self, hap_path: str, reason: str = None):
        self.hap_path = hap_path
        self.reason = reason
        msg = f"应用安装失败: {hap_path}"
        if reason:
            msg += f" - {reason}"
        super().__init__(msg, "APP_INSTALL_FAILED")


class AppNotRunningError(AppError):
    """应用未运行"""
    
    def __init__(self, bundle_name: str):
        self.bundle_name = bundle_name
        super().__init__(
            f"应用 {bundle_name} 未运行",
            "APP_NOT_RUNNING"
        )


class AbilityNotFoundError(AppError):
    """Ability 不存在"""
    
    def __init__(self, bundle_name: str, ability_name: str):
        self.bundle_name = bundle_name
        self.ability_name = ability_name
        super().__init__(
            f"在应用 {bundle_name} 中未找到 Ability: {ability_name}",
            "ABILITY_NOT_FOUND"
        )


# ============================================================================
# UI 相关异常
# ============================================================================

class UIError(HarmonyOSMCPError):
    """UI 相关异常基类"""
    pass


class ElementNotFoundError(UIError):
    """元素不存在"""
    
    def __init__(self, selector: str):
        self.selector = selector
        super().__init__(f"未找到匹配的元素: {selector}", "ELEMENT_NOT_FOUND")


class WindowNotFoundError(UIError):
    """窗口不存在"""
    
    def __init__(self, identifier: str):
        self.identifier = identifier
        super().__init__(f"未找到窗口: {identifier}", "WINDOW_NOT_FOUND")


class UITreeParseError(UIError):
    """UI 树解析错误"""
    
    def __init__(self, reason: str = None):
        self.reason = reason
        msg = "UI 树解析失败"
        if reason:
            msg += f": {reason}"
        super().__init__(msg, "UI_TREE_PARSE_ERROR")


# ============================================================================
# 日志相关异常
# ============================================================================

class LogError(HarmonyOSMCPError):
    """日志相关异常基类"""
    pass


class LogFetchError(LogError):
    """日志获取失败"""
    
    def __init__(self, reason: str = None):
        self.reason = reason
        msg = "日志获取失败"
        if reason:
            msg += f": {reason}"
        super().__init__(msg, "LOG_FETCH_ERROR")


class LogSaveError(LogError):
    """日志保存失败"""
    
    def __init__(self, path: str, reason: str = None):
        self.path = path
        self.reason = reason
        msg = f"日志保存失败: {path}"
        if reason:
            msg += f" - {reason}"
        super().__init__(msg, "LOG_SAVE_ERROR")


class PathNotAllowedError(LogError):
    """路径不在白名单内"""
    
    def __init__(self, path: str, allowed_paths: list):
        self.path = path
        self.allowed_paths = allowed_paths
        super().__init__(
            f"路径 {path} 不在白名单内。允许的路径: {allowed_paths}",
            "PATH_NOT_ALLOWED"
        )


# ============================================================================
# 配置相关异常
# ============================================================================

class ConfigError(HarmonyOSMCPError):
    """配置相关异常基类"""
    pass


class HdcNotFoundError(ConfigError):
    """hdc 工具不存在"""
    
    def __init__(self):
        super().__init__(
            "未找到 hdc 工具，请设置 HDC_PATH 环境变量或安装 DevEco Studio",
            "HDC_NOT_FOUND"
        )


class SDKNotFoundError(ConfigError):
    """SDK 不存在"""
    
    def __init__(self):
        super().__init__(
            "未找到 HarmonyOS SDK，请设置 HARMONYOS_SDK_PATH 环境变量",
            "SDK_NOT_FOUND"
        )


# ============================================================================
# 编译相关异常
# ============================================================================

class CompileError(HarmonyOSMCPError):
    """编译相关异常基类"""
    pass


class WSLNotAvailableError(CompileError):
    """WSL 不可用"""
    
    def __init__(self):
        super().__init__(
            "WSL 环境不可用，无法进行交叉编译",
            "WSL_NOT_AVAILABLE"
        )


class ScriptExecutionError(CompileError):
    """脚本执行失败"""
    
    def __init__(self, script_path: str, exit_code: int, stderr: str = None):
        self.script_path = script_path
        self.exit_code = exit_code
        self.stderr = stderr
        msg = f"脚本执行失败(退出码 {exit_code}): {script_path}"
        super().__init__(msg, "SCRIPT_EXECUTION_ERROR")
