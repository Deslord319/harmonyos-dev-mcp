"""fastmcp.tools stub — provides ToolResult base class."""


class ToolResult:
    def __init__(self, content=None, structured_content=None, meta=None, **kwargs):
        self.content = content
        self.structured_content = structured_content
        self.meta = meta or {}
