"""UI tree related tools."""

import asyncio
from typing import Optional

from common.tools.registry import mcp_tool

from ..container import get_hdc
from ..types import ListWindowsResult, UITreeResult
from ..utils.uitree_parser import UITreeParser
from .device_base import ToolBase
from .response import error_result, from_action_result, mcp_response, ok_result


@mcp_tool(category="ui_tree")
@mcp_response("get_ui_tree")
@ToolBase.handle_tool_error("GET_UI_TREE_ERROR", window_id=0, ui_tree={}, node_count=0)
@ToolBase.with_device(window_id=0, ui_tree={}, node_count=0)
async def get_ui_tree(
    device_id: Optional[str] = None,
    bundle_name: Optional[str] = None,
    window_id: Optional[int] = None,
) -> UITreeResult:
    hdc = get_hdc()
    target_window_id = window_id

    if not target_window_id:
        if bundle_name:
            target_window_id = await asyncio.to_thread(hdc.find_window_by_bundle, device_id, bundle_name)
            if not target_window_id:
                return error_result(
                    "WINDOW_NOT_FOUND",
                    f"window not found for bundle: {bundle_name}",
                    result={"device_id": device_id, "window_id": 0, "ui_tree": {}, "node_count": 0},
                )
        else:
            window_list = await asyncio.to_thread(hdc.get_window_list, device_id)
            windows = window_list.get("windows", []) if isinstance(window_list, dict) else []
            window_check = from_action_result(
                window_list,
                default_code="LIST_WINDOWS_ERROR",
                default_detail="failed to list windows",
                default_result={"windows": windows},
            )
            if not window_check.get("ok", False) or not windows:
                return error_result(
                    "NO_WINDOWS",
                    "no window found",
                    result={"device_id": device_id, "window_id": 0, "ui_tree": {}, "node_count": 0},
                )
            for window in windows:
                if window.get("is_visible"):
                    target_window_id = window.get("window_id")
                    break
            if not target_window_id:
                target_window_id = windows[0].get("window_id", 0)

    ui_tree_result = await asyncio.to_thread(hdc.get_ui_tree_raw, device_id, target_window_id)
    ui_tree_check = from_action_result(
        ui_tree_result,
        default_code="UI_TREE_FETCH_ERROR",
        default_detail="failed to fetch ui tree",
        default_result={
            "device_id": device_id,
            "window_id": target_window_id,
            "ui_tree": {},
            "node_count": 0,
        },
    )
    if not ui_tree_check.get("ok", False):
        return ui_tree_check

    parser = UITreeParser()
    parsed_tree = parser.parse(ui_tree_result.get("ui_tree"))
    node_count = parsed_tree.get("count", 0) if isinstance(parsed_tree, dict) else 0
    return ok_result(
        {
            "device_id": device_id,
            "window_id": target_window_id,
            "ui_tree": parsed_tree,
            "node_count": node_count,
        }
    )


@mcp_tool(category="ui_tree")
@mcp_response("list_windows")
@ToolBase.handle_tool_error("LIST_WINDOWS_ERROR", windows=[], count=0)
@ToolBase.with_device(windows=[], count=0)
async def list_windows(device_id: Optional[str] = None) -> ListWindowsResult:
    hdc = get_hdc()
    raw = await asyncio.to_thread(hdc.get_window_list, device_id)
    windows = raw.get("windows", []) if isinstance(raw, dict) else []
    for w in windows:
        w.setdefault("bundle_name", "")
        w.setdefault("is_visible", False)
        w.setdefault("bounds", {"left": 0, "top": 0, "right": 0, "bottom": 0})

    return from_action_result(
        raw,
        default_code="LIST_WINDOWS_ERROR",
        default_detail="failed to list windows",
        default_result={"device_id": device_id, "windows": windows, "count": raw.get("count", len(windows))},
    )
