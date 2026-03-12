"""UI tree related tools."""

import asyncio
import json
from typing import Optional

from common.tools.registry import mcp_tool

from ..container import get_hdc
from ..types import ListWindowsResult, UITreeResult
from ..utils.ui_common import normalize_bundle_name, rect_to_bounds
from ..utils.uitree_parser import UITreeParser
from .device_base import ToolBase
from .response import error_result, from_action_result, mcp_response, ok_result


async def _resolve_target_window(
    *,
    hdc,
    device_id: str,
    bundle_name: Optional[str],
    window_id: Optional[int],
) -> tuple[bool, dict]:
    resolved = await asyncio.to_thread(
        hdc.resolve_window_target,
        device_id,
        bundle_name=bundle_name,
        window_id=window_id,
    )
    if not resolved.get("success", False):
        return False, error_result(
            resolved.get("error_code", "WINDOW_RESOLUTION_ERROR"),
            resolved.get("error", "failed to resolve target window"),
            result={"device_id": device_id, "window_id": 0, "validated_window_id": None, "validation_applied": True, "capture_scope": "validated_global_dump", "ui_tree": {}, "node_count": 0},
        )
    return True, resolved.get("window") or {"window_id": 0}


@mcp_tool(category="e2e")
@mcp_response("get_ui_tree")
@ToolBase.handle_tool_error(
    "GET_UI_TREE_ERROR",
    window_id=0,
    validated_window_id=None,
    validation_applied=False,
    capture_scope="global_dump",
    ui_tree={},
    node_count=0,
)
@ToolBase.with_device(
    window_id=0,
    validated_window_id=None,
    validation_applied=False,
    capture_scope="global_dump",
    ui_tree={},
    node_count=0,
)
async def get_ui_tree(
    device_id: Optional[str] = None,
    bundle_name: Optional[str] = None,
    window_id: Optional[int] = None,
) -> UITreeResult:
    hdc = get_hdc()
    target_window_id = window_id
    validation_applied = bool(bundle_name or window_id is not None)
    validated_window_id = None

    if validation_applied:
        ok, target_window = await _resolve_target_window(
            hdc=hdc,
            device_id=device_id,
            bundle_name=bundle_name,
            window_id=window_id,
        )
        if not ok:
            return target_window
        target_window_id = target_window.get("window_id", 0)
        validated_window_id = target_window_id

    ui_tree_result = await asyncio.to_thread(hdc.get_ui_tree_raw, device_id, target_window_id)
    ui_tree_check = from_action_result(
        ui_tree_result,
        default_code="UI_TREE_FETCH_ERROR",
        default_detail="failed to fetch ui tree",
        default_result={
            "device_id": device_id,
            "window_id": target_window_id,
            "validated_window_id": validated_window_id,
            "validation_applied": validation_applied,
            "capture_scope": "validated_global_dump" if validation_applied else "global_dump",
            "ui_tree": {},
            "node_count": 0,
        },
    )
    if not ui_tree_check.get("ok", False):
        return ui_tree_check

    raw_tree = ui_tree_result.get("ui_tree")
    parser = UITreeParser()
    if isinstance(raw_tree, dict):
        parsed_tree = parser.parse(json.dumps(raw_tree))
    else:
        parsed_tree = parser.parse(raw_tree)
    node_count = parsed_tree.get("count", 0) if isinstance(parsed_tree, dict) else 0
    return ok_result(
        {
            "device_id": device_id,
            "window_id": target_window_id,
            "validated_window_id": validated_window_id,
            "validation_applied": validation_applied,
            "capture_scope": "validated_global_dump" if validation_applied else "global_dump",
            "ui_tree": parsed_tree,
            "node_count": node_count,
        }
    )


@mcp_tool(category="e2e")
@mcp_response("list_windows")
@ToolBase.handle_tool_error("LIST_WINDOWS_ERROR", windows=[], count=0)
@ToolBase.with_device(windows=[], count=0)
async def list_windows(
    device_id: Optional[str] = None,
    bundle_name: Optional[str] = None,
) -> ListWindowsResult:
    hdc = get_hdc()
    raw = await asyncio.to_thread(hdc.get_window_list, device_id)
    windows = raw.get("windows", []) if isinstance(raw, dict) else []
    for w in windows:
        window_bundle_name = w.get("bundle_name")
        if not isinstance(window_bundle_name, str):
            window_bundle_name = ""
        w["bundle_name"] = window_bundle_name
        w["bundle_name_resolved"] = bool(window_bundle_name)
        w.setdefault("is_visible", False)
        w["bounds"] = rect_to_bounds(w.get("rect"))

    target_bundle = normalize_bundle_name(bundle_name)
    if target_bundle:
        windows = [w for w in windows if normalize_bundle_name(w.get("bundle_name")) == target_bundle]
    if isinstance(raw, dict):
        raw = dict(raw)
        raw["windows"] = windows
        raw["count"] = len(windows)

    return from_action_result(
        raw,
        default_code="LIST_WINDOWS_ERROR",
        default_detail="failed to list windows",
        default_result={"device_id": device_id, "windows": windows, "count": len(windows)},
    )
