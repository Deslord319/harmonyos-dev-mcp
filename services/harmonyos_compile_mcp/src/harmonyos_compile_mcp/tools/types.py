"""
类型定义模块 - 编译验证工具专用

定义 verify_compile_result 工具的返回类型。
"""

from typing import List, Any

from common.types import BaseResult


class VerifyCompileResult(BaseResult):
    """verify_compile_result 返回类型"""

    so_files: List[Any]
    verified: bool
    so_count: int
    valid_count: int
