"""mcp.types stub — provides CallToolResult."""


class CallToolResult:
    def __init__(self, content=None, structuredContent=None, isError=False, _meta=None, **kwargs):
        self.content = content
        self.structuredContent = structuredContent
        self.isError = isError
        self._meta = _meta or {}
