"""Wait tools for E2E flows."""

import asyncio
from typing import Any, Dict, Optional

from common.tools.registry import mcp_tool

from ..container import get_ui_operations
from ..types import UIElement, WaitElementResult, WaitElementState
from .device_base import ToolBase
from .response import error_result, from_action_result, mcp_response, ok_result


def _validate_search_target(
    *,
    text: Optional[str] = None,
    element_type: Optional[str] = None,
    element_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    if any([text, element_type, element_id]):
        return None
    return error_result(
        "INVALID_WAIT_TARGET",
        "must provide at least one of text/element_type/element_id",
        result={"element": None, "elapsed_ms": 0},
    )


def _build_bounds(element: Dict[str, Any]) -> Optional[Dict[str, int]]:
    if isinstance(element.get("bounds"), dict):
        return dict(element["bounds"])
    left = element.get("left")
    top = element.get("top")
    width = element.get("width")
    height = element.get("height")
    if None in (left, top, width, height):
        return None
    return {
        "left": int(left),
        "top": int(top),
        "right": int(left) + int(width),
        "bottom": int(top) + int(height),
    }


def _normalize_element(
    element: Dict[str, Any],
    *,
    bundle_name: Optional[str],
    window_id: Optional[int],
) -> UIElement:
    normalized = dict(element)
    bounds = _build_bounds(normalized)
    if bounds:
        normalized["bounds"] = bounds
    handle = {
        "window_id": normalized.get("window_id", window_id),
        "id": normalized.get("id"),
        "compid": normalized.get("compid"),
        "type": normalized.get("type"),
        "text": normalized.get("text"),
        "x": normalized.get("x"),
        "y": normalized.get("y"),
        "bounds": normalized.get("bounds"),
        "bundle_name": bundle_name,
    }
    normalized["element_handle"] = {k: v for k, v in handle.items() if v is not None}
    return normalized


@mcp_tool(category="e2e")
@mcp_response("wait_element")
@ToolBase.handle_tool_error("WAIT_ELEMENT_ERROR", state="found", satisfied=False, elapsed_ms=0, element=None)
@ToolBase.with_device(state="found", satisfied=False, elapsed_ms=0, element=None)
async def wait_element(
    device_id: Optional[str] = None,
    bundle_name: Optional[str] = None,
    window_id: Optional[int] = None,
    text: Optional[str] = None,
    element_type: Optional[str] = None,
    element_id: Optional[str] = None,
    state: WaitElementState = "found",
    timeout_ms: int = 5000,
    interval_ms: int = 300,
) -> WaitElementResult:
    invalid = _validate_search_target(text=text, element_type=element_type, element_id=element_id)
    if invalid:
        invalid["structuredContent"]["result"]["state"] = state
        invalid["structuredContent"]["result"]["satisfied"] = False
        return invalid
    if state not in ("found", "gone"):
        return error_result(
            "INVALID_WAIT_STATE",
            'state must be "found" or "gone"',
            result={"device_id": device_id, "state": state, "satisfied": False, "elapsed_ms": 0, "element": None},
        )

    ui_ops = get_ui_operations()
    started = asyncio.get_running_loop().time()
    deadline = started + max(timeout_ms, 0) / 1000

    while True:
        raw = await asyncio.to_thread(
            ui_ops.find_element,
            device_id,
            text=text,
            element_type=element_type,
            element_id=element_id,
            bundle_name=bundle_name,
            window_id=window_id,
        )
        elapsed_ms = int((asyncio.get_running_loop().time() - started) * 1000)
        if not raw.get("success", False):
            return from_action_result(
                raw,
                default_code="FIND_ELEMENT_ERROR",
                default_detail="find element failed",
                default_result={
                    "device_id": device_id,
                    "state": state,
                    "satisfied": False,
                    "elapsed_ms": elapsed_ms,
                    "element": None,
                },
            )

        elements = raw.get("elements", [])
        if state == "found":
            if elements:
                return ok_result(
                    {
                        "device_id": device_id,
                        "state": state,
                        "satisfied": True,
                        "elapsed_ms": elapsed_ms,
                        "element": _normalize_element(
                            elements[0],
                            bundle_name=bundle_name,
                            window_id=raw.get("window_id", window_id),
                        ),
                    }
                )
            if asyncio.get_running_loop().time() >= deadline:
                return error_result(
                    "WAIT_TIMEOUT",
                    f'element did not reach state "{state}" within {timeout_ms}ms',
                    result={
                        "device_id": device_id,
                        "state": state,
                        "satisfied": False,
                        "elapsed_ms": elapsed_ms,
                        "element": None,
                    },
                )
        else:
            if not elements:
                return ok_result(
                    {"device_id": device_id, "state": state, "satisfied": True, "elapsed_ms": elapsed_ms, "element": None}
                )
            if asyncio.get_running_loop().time() >= deadline:
                return error_result(
                    "WAIT_TIMEOUT",
                    f'element did not reach state "{state}" within {timeout_ms}ms',
                    result={
                        "device_id": device_id,
                        "state": state,
                        "satisfied": False,
                        "elapsed_ms": elapsed_ms,
                        "element": _normalize_element(
                            elements[0],
                            bundle_name=bundle_name,
                            window_id=raw.get("window_id", window_id),
                        ),
                    },
                )

        await asyncio.sleep(max(interval_ms, 0) / 1000)
