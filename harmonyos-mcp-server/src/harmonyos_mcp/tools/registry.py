"""
MCP 工具自动注册机制

提供 @mcp_tool 装饰器和全局注册表，替代 server.py 中的手动逐一注册。

Usage:
    # 在工具模块中标记工具函数
    @mcp_tool(category="device")
    def list_devices() -> ListDevicesResult:
        ...

    # 在 server.py 中自动注册所有已标记的工具
    from .tools.registry import get_registered_tools
    for entry in get_registered_tools():
        server.tool()(entry.func)
"""
from typing import List, Callable
from dataclasses import dataclass


@dataclass
class ToolEntry:
    """已注册的工具条目"""
    func: Callable
    category: str


# 全局工具注册表
_registry: List[ToolEntry] = []


def mcp_tool(category: str = "default"):
    """
    MCP 工具注册装饰器

    装饰后的函数会被自动收集到全局注册表中，
    在 server.py 导入工具模块时触发注册。

    Args:
        category: 工具分类（device/build/packages/ui/ui_tree/logs/compile）

    Returns:
        原函数（不改变签名和行为）
    """
    def decorator(func: Callable) -> Callable:
        _registry.append(ToolEntry(func=func, category=category))
        # 在函数上标记分类，便于调试和内省
        func._mcp_category = category
        return func
    return decorator


def get_registered_tools() -> List[ToolEntry]:
    """获取所有已注册的工具列表"""
    return list(_registry)


def get_tools_by_category(category: str) -> List[ToolEntry]:
    """按分类获取工具列表"""
    return [entry for entry in _registry if entry.category == category]


def get_tool_summary() -> dict:
    """
    获取工具注册摘要

    Returns:
        {
            "total": 28,
            "categories": {"device": 2, "build": 4, ...}
        }
    """
    categories: dict = {}
    for entry in _registry:
        categories[entry.category] = categories.get(entry.category, 0) + 1
    return {
        "total": len(_registry),
        "categories": categories,
    }


def clear_registry() -> None:
    """清空注册表（用于测试）"""
    _registry.clear()
