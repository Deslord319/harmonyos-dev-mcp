"""fastmcp stub — provides empty FastMCP and ToolResult, no real implementation."""


class FastMCP:
    def __init__(self, name=""):
        self.name = name

    def tool(self, *args, **kwargs):
        def decorator(func):
            return func
        return decorator

    def run(self, *args, **kwargs):
        pass
