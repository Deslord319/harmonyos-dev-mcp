"""
异常基类

定义 MCP 服务的基础异常。
"""


class MCPError(Exception):
    """MCP 服务基础异常"""

    def __init__(self, message: str, code: str = "UNKNOWN_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code

    def to_dict(self) -> dict:
        return {
            "success": False,
            "error": self.message,
            "error_code": self.code,
        }
