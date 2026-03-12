"""UI tree related tools."""

import asyncio
import json
from typing import Optional

from common.tools.registry import mcp_tool

from ..container import get_hdc
from ..types import ListWindowsResult, UITreeResult
from ..utils.uitree_parser import UITreeParser
from .device_base import ToolBase
from .response import error_result, from_action_result, mcp_response, ok_result


def _rect_to_bounds(rect: Optional[dict]) -> dict:
    if not isinstance(rect, dict):
        return {"left": 0, "top": 0, "right": 0, "bottom": 0}
    x = int(rect.get("x", 0))
    y = int(rect.get("y", 0))
    w = int(rect.get("w", 0))
    h = int(rect.get("h", 0))
    return {"left": x, "top": y, "right": x + w, "bottom": y + h}


def _normalize_bundle_name(bundle_name: Optional[str]) -> str:
    return bundle_name.strip() if isinstance(bundle_name, str) else ""


def _window_matches_bundle(window: dict, bundle_name: Optional[str]) -> bool:
    target = _normalize_bundle_name(bundle_name)
    if not target:
        return True

    actual = _normalize_bundle_name(window.get("bundle_name"))
    return bool(actual) and actual == target


def _pick_visible_window(windows: list[dict]) -> Optional[dict]:
    for window in windows:
        if window.get("is_visible"):
            return window
    return windows[0] if windows else None


async def _resolve_target_window(
    *,
    hdc,
    device_id: str,
    bundle_name: Optional[str],
    window_id: Optional[int],
) -> tuple[bool, dict]:
    target_bundle = _normalize_bundle_name(bundle_name)
    window_list = await asyncio.to_thread(hdc.get_window_list, device_id)
    windows = window_list.get("windows", []) if isinstance(window_list, dict) else []
    window_check = from_action_result(
        window_list,
        default_code="LIST_WINDOWS_ERROR",
        default_detail="failed to list windows",
        default_result={"windows": windows},
    )
    if not window_check.get("ok", False):
        return False, error_result(
            window_check.get("error", {}).get("code", "LIST_WINDOWS_ERROR"),
            window_check.get("error", {}).get("detail", "failed to list windows"),
            result={"device_id": device_id, "window_id": 0, "ui_tree": {}, "node_count": 0},
        )
    if not windows:
        return False, error_result(
            "NO_WINDOWS",
            "no window found",
            result={"device_id": device_id, "window_id": 0, "ui_tree": {}, "node_count": 0},
        )

    matched_window = None
    if window_id is not None:
        matched_window = next((w for w in windows if w.get("window_id") == window_id), None)
        if not matched_window:
            return False, error_result(
                "WINDOW_NOT_FOUND",
                f"window not found: {window_id}",
                result={"device_id": device_id, "window_id": 0, "ui_tree": {}, "node_count": 0},
            )
        if target_bundle and not _window_matches_bundle(matched_window, target_bundle):
            return False, error_result(
                "WINDOW_BUNDLE_MISMATCH",
                f"window {window_id} does not match bundle: {target_bundle}",
                result={"device_id": device_id, "window_id": window_id, "ui_tree": {}, "node_count": 0},
            )
        return True, matched_window

    if target_bundle:
        visible_matches = [w for w in windows if w.get("is_visible") and _window_matches_bundle(w, target_bundle)]
        matched_window = visible_matches[0] if visible_matches else None
        if not matched_window:
            any_matches = [w for w in windows if _window_matches_bundle(w, target_bundle)]
            matched_window = any_matches[0] if any_matches else None
        if not matched_window:
            return False, error_result(
                "WINDOW_NOT_FOUND",
                f"window not found for bundle: {target_bundle}",
                result={"device_id": device_id, "window_id": 0, "ui_tree": {}, "node_count": 0},
            )
        return True, matched_window

    matched_window = _pick_visible_window(windows)
    return True, matched_window or {"window_id": 0}


@mcp_tool(category="e2e")
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

    if bundle_name or window_id is not None:
        ok, target_window = await _resolve_target_window(
            hdc=hdc,
            device_id=device_id,
            bundle_name=bundle_name,
            window_id=window_id,
        )
        if not ok:
            return target_window
        target_window_id = target_window.get("window_id", 0)

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
        w["bounds"] = _rect_to_bounds(w.get("rect"))

    target_bundle = _normalize_bundle_name(bundle_name)
    if target_bundle:
        windows = [w for w in windows if _normalize_bundle_name(w.get("bundle_name")) == target_bundle]
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
