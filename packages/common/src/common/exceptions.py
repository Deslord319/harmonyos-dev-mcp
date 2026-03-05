"""
寮傚父鍩虹被

瀹氫箟 MCP 鏈嶅姟鐨勫熀纭€寮傚父銆?"""


class MCPError(Exception):
    """MCP 鏈嶅姟鍩虹寮傚父"""

    def __init__(self, message: str, code: str = "UNKNOWN_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code

    def to_dict(self) -> dict:
        return {
            "tool": "unknown",
            "ok": False,
            "result": None,
            "error": {
                "code": self.code,
                "detail": self.message,
            },
            "meta": {},
        }

