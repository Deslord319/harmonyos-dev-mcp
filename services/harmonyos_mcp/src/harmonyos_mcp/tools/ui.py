"""UI automation tools."""

import asyncio
import os
from datetime import datetime
from typing import Optional, Tuple, Union

from common.tools.registry import mcp_tool

from ..container import get_hdc, get_ui_operations
from ..types import (
    ClickResult,
    DragResult,
    ElementScreenshotResult,
    FindElementResult,
    InputTextResult,
    LongPressResult,
    PressKeyResult,
    ScreenshotResult,
    SwipeResult,
)
from .device_base import ToolBase
from .response import error_result, from_action_result, mcp_response


async def _resolve_element_coords(
    device_id: str,
    text: Optional[str] = None,
    element_type: Optional[str] = None,
    bundle_name: Optional[str] = None,
) -> Tuple[bool, Union[Tuple[int, int], dict]]:
    ui_ops = get_ui_operations()
    raw = await asyncio.to_thread(
        ui_ops.find_element,
        device_id,
        text=text,
        element_type=element_type,
        bundle_name=bundle_name,
    )
    if not raw.get("success", False):
        return False, from_action_result(
            raw,
            default_code="FIND_ELEMENT_ERROR",
            default_detail="find element failed",
            default_result={"elements": [], "count": 0},
        )

    elements = raw.get("elements", [])
    if not elements:
        return False, error_result(
            "ELEMENT_NOT_FOUND",
            f"element not found: text={text}, type={element_type}",
            result={"elements": [], "count": 0},
        )

    element = elements[0]
    if "x" not in element or "y" not in element:
        return False, error_result(
            "INVALID_ELEMENT_COORDS",
            f"invalid element coords: {element}",
            result={"elements": elements, "count": len(elements)},
        )
    return True, (element["x"], element["y"])


@mcp_tool(category="ui")
@mcp_response("click_element")
@ToolBase.handle_tool_error("CLICK_ERROR", x=0, y=0)
@ToolBase.with_device(x=0, y=0)
async def click_element(
    device_id: Optional[str] = None,
    x: Optional[int] = None,
    y: Optional[int] = None,
    text: Optional[str] = None,
    element_type: Optional[str] = None,
    double_click: bool = False,
    bundle_name: Optional[str] = None,
) -> ClickResult:
    has_coords = x is not None and y is not None
    has_search = bool(text or element_type)

    if has_coords and has_search:
        return error_result(
            "PARAM_CONFLICT",
            "cannot provide both coordinates and search criteria",
            result={"x": x, "y": y},
        )

    ui_ops = get_ui_operations()

    if has_coords:
        raw = await asyncio.to_thread(ui_ops.double_click if double_click else ui_ops.click, device_id, x, y)
        return from_action_result(
            raw,
            default_code="CLICK_ERROR",
            default_detail="click failed",
            default_result={"x": x, "y": y},
        )

    if has_search:
        ok, coords = await _resolve_element_coords(device_id, text=text, element_type=element_type, bundle_name=bundle_name)
        if not ok:
            return coords
        ex, ey = coords
        raw = await asyncio.to_thread(ui_ops.double_click if double_click else ui_ops.click, device_id, ex, ey)
        return from_action_result(
            raw,
            default_code="CLICK_ERROR",
            default_detail="click failed",
            default_result={"x": ex, "y": ey},
        )

    return error_result(
        "MISSING_PARAMS",
        "must provide (x,y) or (text/element_type)",
        result={"x": x or 0, "y": y or 0},
    )


@mcp_tool(category="ui")
@mcp_response("long_press_element")
@ToolBase.handle_tool_error("LONG_PRESS_ERROR")
@ToolBase.with_device()
async def long_press_element(
    device_id: Optional[str] = None,
    x: Optional[int] = None,
    y: Optional[int] = None,
    text: Optional[str] = None,
    element_type: Optional[str] = None,
    bundle_name: Optional[str] = None,
) -> LongPressResult:
    ui_ops = get_ui_operations()

    if x is not None and y is not None:
        raw = await asyncio.to_thread(ui_ops.long_click, device_id, x, y)
        return from_action_result(
            raw,
            default_code="LONG_PRESS_ERROR",
            default_detail="long press failed",
            default_result={"x": x, "y": y},
        )

    if text or element_type:
        ok, coords = await _resolve_element_coords(device_id, text=text, element_type=element_type, bundle_name=bundle_name)
        if not ok:
            return coords
        ex, ey = coords
        raw = await asyncio.to_thread(ui_ops.long_click, device_id, ex, ey)
        return from_action_result(
            raw,
            default_code="LONG_PRESS_ERROR",
            default_detail="long press failed",
            default_result={"x": ex, "y": ey},
        )

    return error_result("MISSING_PARAMS", "must provide coordinates or search criteria", result={"x": 0, "y": 0})


@mcp_tool(category="ui")
@mcp_response("swipe")
@ToolBase.handle_tool_error("SWIPE_ERROR", from_x=0, from_y=0, to_x=0, to_y=0, direction=None)
@ToolBase.with_device(from_x=0, from_y=0, to_x=0, to_y=0, direction=None)
async def swipe(
    device_id: Optional[str] = None,
    from_x: Optional[int] = None,
    from_y: Optional[int] = None,
    to_x: Optional[int] = None,
    to_y: Optional[int] = None,
    direction: Optional[str] = None,
    speed: int = 600,
) -> SwipeResult:
    default_result = {
        "from_x": from_x or 0,
        "from_y": from_y or 0,
        "to_x": to_x or 0,
        "to_y": to_y or 0,
        "direction": direction,
    }

    ui_ops = get_ui_operations()

    if direction:
        raw = await asyncio.to_thread(ui_ops.swipe_direction, device_id, direction, speed)
        return from_action_result(
            raw,
            default_code="SWIPE_ERROR",
            default_detail="swipe failed",
            default_result=default_result,
        )

    if all(v is not None for v in [from_x, from_y, to_x, to_y]):
        raw = await asyncio.to_thread(ui_ops.swipe, device_id, from_x, from_y, to_x, to_y, speed)
        return from_action_result(
            raw,
            default_code="SWIPE_ERROR",
            default_detail="swipe failed",
            default_result=default_result,
        )

    return error_result("MISSING_PARAMS", "must provide swipe coords or direction", result=default_result)


@mcp_tool(category="ui")
@mcp_response("input_text")
@ToolBase.handle_tool_error("INPUT_TEXT_ERROR", text="", x=0, y=0)
@ToolBase.with_device(text="", x=0, y=0)
async def input_text(
    device_id: Optional[str] = None,
    x: Optional[int] = None,
    y: Optional[int] = None,
    text: Optional[str] = None,
    element_text: Optional[str] = None,
    element_type: Optional[str] = None,
    bundle_name: Optional[str] = None,
) -> InputTextResult:
    default_result = {"text": text or "", "x": x or 0, "y": y or 0}

    if not text:
        return error_result("MISSING_TEXT", "text is required", result=default_result)

    ui_ops = get_ui_operations()

    if x is not None and y is not None:
        raw = await asyncio.to_thread(ui_ops.input_text, device_id, x, y, text)
        return from_action_result(
            raw,
            default_code="INPUT_TEXT_ERROR",
            default_detail="input text failed",
            default_result=default_result,
        )

    if element_text or element_type:
        ok, coords = await _resolve_element_coords(device_id, text=element_text, element_type=element_type, bundle_name=bundle_name)
        if not ok:
            return coords
        ex, ey = coords
        raw = await asyncio.to_thread(ui_ops.input_text, device_id, ex, ey, text)
        return from_action_result(
            raw,
            default_code="INPUT_TEXT_ERROR",
            default_detail="input text failed",
            default_result={"text": text, "x": ex, "y": ey},
        )

    return error_result("MISSING_PARAMS", "must provide coordinates or search criteria", result=default_result)


@mcp_tool(category="ui")
@mcp_response("press_key")
@ToolBase.handle_tool_error("PRESS_KEY_ERROR", key="")
@ToolBase.with_device(key="")
async def press_key(device_id: Optional[str] = None, key: Optional[str] = None) -> PressKeyResult:
    if not key:
        return error_result("MISSING_KEY", "key is required", result={"key": ""})

    ui_ops = get_ui_operations()
    raw = await asyncio.to_thread(ui_ops.press_key, device_id, key)
    return from_action_result(
        raw,
        default_code="PRESS_KEY_ERROR",
        default_detail="press key failed",
        default_result={"key": key},
    )


@mcp_tool(category="ui")
@mcp_response("find_element")
@ToolBase.handle_tool_error("FIND_ELEMENT_ERROR", elements=[], count=0)
@ToolBase.with_device(elements=[], count=0)
async def find_element(
    device_id: Optional[str] = None,
    text: Optional[str] = None,
    element_type: Optional[str] = None,
    element_id: Optional[str] = None,
    bundle_name: Optional[str] = None,
) -> FindElementResult:
    if not any([text, element_type, element_id]):
        return error_result(
            "MISSING_SEARCH_CRITERIA",
            "must provide at least one of text/element_type/element_id",
            result={"elements": [], "count": 0},
        )

    ui_ops = get_ui_operations()
    raw = await asyncio.to_thread(
        ui_ops.find_element,
        device_id,
        text=text,
        element_type=element_type,
        element_id=element_id,
        bundle_name=bundle_name,
    )
    base = {"elements": raw.get("elements", []), "count": raw.get("count", len(raw.get("elements", [])))}
    return from_action_result(
        raw,
        default_code="FIND_ELEMENT_ERROR",
        default_detail="find element failed",
        default_result=base,
    )


@mcp_tool(category="ui")
@mcp_response("screenshot")
@ToolBase.handle_tool_error("SCREENSHOT_ERROR")
@ToolBase.with_device()
@ToolBase.validate_params(local_path=["path"])
async def screenshot(
    device_id: Optional[str] = None,
    local_path: Optional[str] = None,
    display_id: int = 0,
    left: Optional[int] = None,
    top: Optional[int] = None,
    right: Optional[int] = None,
    bottom: Optional[int] = None,
) -> ScreenshotResult:
    hdc = get_hdc()

    if not local_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshots_dir = os.path.join(os.path.expanduser("~"), "harmonyos-screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)
        suffix = "element" if left is not None else "screenshot"
        local_path = os.path.join(screenshots_dir, f"{suffix}_{timestamp}.jpeg")

    if left is not None and top is not None and right is not None and bottom is not None:
        bounds = {"left": left, "top": top, "right": right, "bottom": bottom}
        raw = await asyncio.to_thread(hdc.take_element_screenshot, device_id, local_path, bounds)
        return from_action_result(
            raw,
            default_code="SCREENSHOT_ERROR",
            default_detail="element screenshot failed",
            default_result={"bounds": bounds},
        )

    raw = await asyncio.to_thread(hdc.take_screenshot, device_id, local_path, display_id)
    return from_action_result(
        raw,
        default_code="SCREENSHOT_ERROR",
        default_detail="screenshot failed",
    )


@mcp_tool(category="ui")
@mcp_response("drag")
@ToolBase.handle_tool_error("DRAG_ERROR")
@ToolBase.with_device()
async def drag(
    device_id: Optional[str] = None,
    from_x: Optional[int] = None,
    from_y: Optional[int] = None,
    to_x: Optional[int] = None,
    to_y: Optional[int] = None,
    speed: int = 600,
) -> DragResult:
    if not all(v is not None for v in [from_x, from_y, to_x, to_y]):
        return error_result(
            "MISSING_PARAMS",
            "must provide from_x, from_y, to_x, to_y",
            result={"from_x": from_x or 0, "from_y": from_y or 0, "to_x": to_x or 0, "to_y": to_y or 0},
        )

    ui_ops = get_ui_operations()
    raw = await asyncio.to_thread(ui_ops.drag, device_id, from_x, from_y, to_x, to_y, speed)
    return from_action_result(
        raw,
        default_code="DRAG_ERROR",
        default_detail="drag failed",
        default_result={"from_x": from_x, "from_y": from_y, "to_x": to_x, "to_y": to_y},
    )
