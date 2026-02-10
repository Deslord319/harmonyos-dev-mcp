"""
异常定义模块

定义所有自定义异常类，提供统一的错误处理机制。
仅保留被导出或实际使用的异常类。
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


# ============================================================================
# 构建相关异常
# ============================================================================

class BuildError(HarmonyOSMCPError):
    """构建相关异常基类"""
    pass


class BuildFailedError(BuildError):
    """构建失败"""
    
    def __init__(self, project_path: str, reason: str = None):
        self.project_path = project_path
        self.reason = reason
        msg = f"项目构建失败: {project_path}"
        if reason:
            msg += f" - {reason}"
        super().__init__(msg, "BUILD_FAILED")


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
