"""
HarmonyOS 编译验证工具

提供 .so 文件验证功能。
编译流程由 AI 生成脚本，用户在本地执行。
"""

import asyncio
from typing import Optional

from ..container import get_compile_manager
from .types import VerifyCompileResult
from common.tools.base import ToolBase
from common.tools.registry import mcp_tool
from common.tools.response import from_action_result, mcp_response


@mcp_tool(category="compile")
@mcp_response("verify_compile_result")
@ToolBase.handle_tool_error("VERIFY_COMPILE_ERROR")
async def verify_compile_result(
    project_dir: str, output_dir: Optional[str] = None
) -> VerifyCompileResult:
    """
    验证编译输出的 .so 文件

    Args:
        project_dir: 项目目录路径
        output_dir: 输出目录（可选，默认为 project_dir/build_harmonyos）

    Returns:
        验证结果，包含文件检查、格式验证等信息
    """
    manager = get_compile_manager()
    raw = await asyncio.to_thread(
        manager.verify_so_output, project_dir=project_dir, output_dir=output_dir
    )
    return from_action_result(
        raw,
        default_code="VERIFY_COMPILE_ERROR",
        default_detail="verify compile result failed",
    )
