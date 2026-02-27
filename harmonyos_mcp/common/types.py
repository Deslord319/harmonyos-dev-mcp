"""
通用响应类型

提供 BaseResult 基础类型，所有工具返回类型都应继承自此。
"""
from typing import TypedDict


class BaseResult(TypedDict, total=False):
    """所有工具返回的基础类型"""
    success: bool
    error: str
    message: str
