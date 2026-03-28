"""HarmonyOS compile verification tools."""

import asyncio
from typing import Optional

from common.tools.base import ToolBase
from common.tools.registry import mcp_tool
from common.tools.response import from_action_result, mcp_response

from ..container import get_compile_manager
from .types import VerifyCompileResult


@mcp_tool(category="compile")
@mcp_response("verify_compile_result")
@ToolBase.handle_tool_error("VERIFY_COMPILE_ERROR")
async def verify_compile_result(project_dir: str, output_dir: Optional[str] = None) -> VerifyCompileResult:
    """Verify compiled `.so` outputs for a HarmonyOS project."""
    manager = get_compile_manager()
    raw = await asyncio.to_thread(manager.verify_so_output, project_dir=project_dir, output_dir=output_dir)
    return from_action_result(
        raw,
        default_code="VERIFY_COMPILE_ERROR",
        default_detail="verify compile result failed",
    )
