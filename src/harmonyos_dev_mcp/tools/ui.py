"""UI automation tools."""

import asyncio
import functools
import os
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Tuple, Union
from weakref import WeakKeyDictionary

from harmonyos_dev_mcp._common.tools.registry import mcp_tool
from harmonyos_dev_mcp.config import Config
from harmonyos_dev_mcp.device.hdc.routing import get_hdc_server_override

from ..container import get_hdc, get_ui_operations
from ..types import (
    ClickResult,
    DragResult,
    FindElementsResult,
    InputTextResult,
    LongPressResult,
    PressKeyResult,
    ScreenshotResult,
    SwipeResult,
)
from ..ui.keycodes import KeyCode, ResolvedKey, resolve_key
from ..ui.normalizers.element import attach_element_metadata, build_lookup_hint, compact_candidate_handles
from .device_support import DeviceToolSupport
from harmonyos_dev_mcp._common.tools.response import error_result, from_action_result, mcp_response

_MODIFIER_KEYS = {
    "alt": ("Alt", int(KeyCode.ALT_LEFT)),
    "ctrl": ("Ctrl", int(KeyCode.CTRL_LEFT)),
    "control": ("Ctrl", int(KeyCode.CTRL_LEFT)),
    "meta": ("Meta", int(KeyCode.META_LEFT)),
    "shift": ("Shift", int(KeyCode.SHIFT_LEFT)),
}
_ASCII_PASTE_SENTINEL = "中"
_UI_MUTATION_LOCKS: WeakKeyDictionary = WeakKeyDictionary()


def _device_mutation_lock(device_id: str) -> asyncio.Lock:
    """Return the lock that serializes UI mutations for one routed device."""
    loop = asyncio.get_running_loop()
    hdc_server = get_hdc_server_override() or Config.HARMONYOS_HDC_SERVER or ""
    locks_for_loop = _UI_MUTATION_LOCKS.setdefault(loop, {})
    key = (hdc_server, device_id)
    lock = locks_for_loop.get(key)
    if lock is None:
        lock = asyncio.Lock()
        locks_for_loop[key] = lock
    return lock


def _serialize_ui_mutation(func):
    """Keep a public UI mutation atomic relative to other mutations."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        device_id = kwargs.get("device_id")
        if not device_id:
            return await func(*args, **kwargs)
        async with _device_mutation_lock(device_id):
            return await func(*args, **kwargs)

    return wrapper


def _input_strategy(text: str) -> Tuple[str, str, bool, Optional[str]]:
    """Choose a deterministic UiTest text route using only public device abilities."""
    if text == "":
        return "clear", "", False, None
    if len(text) > 200:
        return "native_paste", text, True, None
    if text.isascii() and text.isdecimal():
        return "direct_key_events", text, False, None
    if not text.isascii():
        return "native_paste", text, True, None
    return (
        "forced_paste_sentinel",
        f"{text}{_ASCII_PASTE_SENTINEL}",
        True,
        _ASCII_PASTE_SENTINEL,
    )


def _with_success_message(raw: Any, message: str) -> Any:
    if not isinstance(raw, dict):
        return raw
    normalized = dict(raw)
    normalized.pop("action", None)
    if normalized.get("success", False):
        normalized["message"] = message
    return normalized


def _with_unverified_dispatch(result: dict, message: str) -> dict:
    """Describe command delivery without claiming an application-level effect."""
    result_data = dict(result.get("result") or {})
    dispatched = bool(result.get("ok", False))
    result_data.update(
        {
            "dispatched": dispatched,
            "effect_verified": False,
        }
    )
    if dispatched:
        result_data["message"] = message
    result["result"] = result_data
    return result


def _is_close(a: Any, b: Any, tolerance: int = 12) -> bool:
    if a is None or b is None:
        return False
    return abs(int(a) - int(b)) <= tolerance


def _resolve_modifier(modifier: str) -> Optional[Tuple[str, int]]:
    alias = str(modifier).strip().replace("-", "_").replace(" ", "_").lower()
    return _MODIFIER_KEYS.get(alias)


def _press_key_result(
    resolved_key: Optional[ResolvedKey],
    *,
    modifiers: Optional[List[str]] = None,
    event_key_codes: Optional[List[int]] = None,
    dispatched: bool = False,
) -> Dict[str, Any]:
    return {
        "key": resolved_key.name if resolved_key is not None else None,
        "key_code": resolved_key.code if resolved_key is not None else None,
        "modifiers": list(modifiers or []),
        "event_key_codes": list(event_key_codes or []),
        "dispatched": dispatched,
        "effect_verified": False,
    }


def _match_handle_candidates(candidates: list[Dict[str, Any]], handle: Dict[str, Any]) -> list[Dict[str, Any]]:
    exact = []
    approximate = []
    for candidate in candidates:
        candidate_window = candidate.get("window_id")
        handle_window = handle.get("window_id")
        if candidate_window is not None and handle_window is not None and candidate_window != handle_window:
            continue

        if handle.get("compid") and candidate.get("compid") == handle.get("compid"):
            exact.append(candidate)
            continue

        if handle.get("id") and candidate.get("id") == handle.get("id"):
            if not handle.get("type") or candidate.get("type") == handle.get("type"):
                exact.append(candidate)
                continue

        if (
            handle.get("type")
            and candidate.get("type") == handle.get("type")
            and _is_close(candidate.get("x"), handle.get("x"))
            and _is_close(candidate.get("y"), handle.get("y"))
        ):
            approximate.append(candidate)

    return exact or approximate


def _resolved_result(
    element: Dict[str, Any],
    *,
    resolved_via: str,
    handle_refreshed: bool,
) -> Dict[str, Any]:
    return {
        "x": int(element["x"]),
        "y": int(element["y"]),
        "element_handle": dict(element.get("element_handle") or {}),
        "resolved_via": resolved_via,
        "handle_refreshed": handle_refreshed,
    }


def _foreground_window_state(
    windows: list[Dict[str, Any]],
    target_window_id: Any,
) -> Dict[str, Any]:
    """Return a conservative foreground classification for one target window."""
    target = next((window for window in windows if window.get("window_id") == target_window_id), None)
    if target is None:
        return {
            "window_foreground": None,
            "foreground_window_id": None,
            "target_window": None,
        }

    display_id = target.get("display_id", 0)
    target_type = target.get("type")
    candidate_types = {1}
    if target_type is not None:
        candidate_types.add(target_type)

    candidates = [
        window
        for window in windows
        if window.get("is_visible")
        and window.get("display_id", 0) == display_id
        and (window.get("type") in candidate_types or window.get("window_id") == target_window_id)
    ]
    candidates_with_zord = [window for window in candidates if window.get("zord") is not None]
    if candidates_with_zord:
        foreground = max(candidates_with_zord, key=lambda window: int(window.get("zord", -1)))
        foreground_window_id = foreground.get("window_id")
        return {
            "window_foreground": foreground_window_id == target_window_id,
            "foreground_window_id": foreground_window_id,
            "target_window": target,
        }

    if len(candidates) == 1 and candidates[0].get("window_id") == target_window_id:
        return {
            "window_foreground": True,
            "foreground_window_id": target_window_id,
            "target_window": target,
        }

    return {
        "window_foreground": None,
        "foreground_window_id": None,
        "target_window": target,
    }


async def _read_foreground_window_state(device_id: str, target_window_id: Any) -> Dict[str, Any]:
    hdc = get_hdc()
    raw = await asyncio.to_thread(hdc.get_window_list, device_id)
    if not isinstance(raw, dict) or not raw.get("success", False):
        return {
            "window_foreground": None,
            "foreground_window_id": None,
            "target_window": None,
            "window_error": (
                raw.get("error", "failed to read window state")
                if isinstance(raw, dict)
                else "failed to read window state"
            ),
        }
    return _foreground_window_state(raw.get("windows", []), target_window_id)


async def _perform_resolved_action(
    *,
    action_fn,
    device_id: str,
    resolved: Dict[str, Any],
    success_message: str,
    default_code: str,
    default_detail: str,
    extra_args: tuple = (),
    extra_result: Optional[Dict[str, Any]] = None,
) -> dict:
    raw = await asyncio.to_thread(action_fn, device_id, resolved["x"], resolved["y"], *extra_args)
    raw = _with_success_message(raw, success_message)
    default_result = dict(resolved)
    if extra_result:
        default_result.update(extra_result)
    return from_action_result(
        raw,
        default_code=default_code,
        default_detail=default_detail,
        default_result=default_result,
    )


async def _perform_unverified_action(
    *,
    dispatch_message: str,
    **kwargs,
) -> dict:
    result = await _perform_resolved_action(**kwargs)
    return _with_unverified_dispatch(result, dispatch_message)


async def _acquire_input_focus(
    *,
    device_id: str,
    resolved: Dict[str, Any],
    default_result: Dict[str, Any],
) -> Tuple[bool, Dict[str, Any]]:
    """Click a handled input and observe focus plus foreground before typing."""
    ui_ops = get_ui_operations()
    focus_raw = await asyncio.to_thread(ui_ops.click, device_id, resolved["x"], resolved["y"])
    focus_dispatched = bool(isinstance(focus_raw, dict) and focus_raw.get("success", False))
    focus_result = {
        **default_result,
        **resolved,
        "focus_dispatched": focus_dispatched,
        "focus_verified": False,
        "focus_observations": 0,
        "focused": None,
        "window_foreground": None,
        "foreground_window_id": None,
        "stage": "focus",
    }
    if not focus_dispatched:
        return False, error_result(
            "INPUT_FOCUS_DISPATCH_FAILED",
            (
                focus_raw.get("error") or focus_raw.get("message") or "failed to dispatch focus click"
                if isinstance(focus_raw, dict)
                else "failed to dispatch focus click"
            ),
            result=focus_result,
        )

    loop = asyncio.get_running_loop()
    started = loop.time()
    timeout_ms = max(0, Config.INPUT_FOCUS_TIMEOUT_MS)
    deadline = started + timeout_ms / 1000
    active_handle = dict(resolved.get("element_handle") or {})
    initial_resolution = resolved.get("resolved_via")
    last_resolution_error: Optional[dict] = None
    window_error: Optional[str] = None

    while loop.time() < deadline:
        verified_ok, verified = await _resolve_handle_coords(device_id, active_handle)
        focus_result["focus_observations"] += 1
        if not verified_ok:
            last_resolution_error = verified
            continue

        active_handle = dict(verified.get("element_handle") or active_handle)
        focus_result.update(verified)
        focus_result["resolved_via"] = initial_resolution
        focus_result["element_handle"] = active_handle
        focus_result["focused"] = active_handle.get("focused")

        if active_handle.get("enabled") is False or active_handle.get("visible") is False:
            return False, error_result(
                "INPUT_TARGET_NOT_INTERACTABLE",
                "input target is disabled or not visible",
                result=focus_result,
            )

        window_state = await _read_foreground_window_state(
            device_id,
            active_handle.get("window_id"),
        )
        focus_result.update(
            {
                "window_foreground": window_state.get("window_foreground"),
                "foreground_window_id": window_state.get("foreground_window_id"),
            }
        )
        window_error = window_state.get("window_error")
        if active_handle.get("focused") is True and window_state.get("window_foreground") is True:
            focus_result.update(
                {
                    "focus_verified": True,
                    "stage": "focused",
                    "elapsed_ms": int((loop.time() - started) * 1000),
                }
            )
            return True, focus_result

    detail = (
        "focus click was dispatched, but the target element did not become focused "
        "in the foreground application window before the deadline"
    )
    if last_resolution_error and focus_result.get("focused") is None:
        detail = "focus click was dispatched, but the target element could not be re-read before the deadline"
    elif window_error and focus_result.get("window_foreground") is None:
        detail = f"focus click was dispatched, but foreground window state could not be read: {window_error}"
    focus_result["elapsed_ms"] = int((loop.time() - started) * 1000)
    return False, error_result(
        "INPUT_FOCUS_TIMEOUT",
        detail,
        result=focus_result,
    )


async def _resolve_handle_coords(
    device_id: str,
    element_handle: Any,
) -> Tuple[bool, Union[Dict[str, Any], dict]]:
    if not isinstance(element_handle, dict):
        return False, error_result(
            "INVALID_ELEMENT_HANDLE",
            "element_handle must be an object taken directly from find_elements/wait_for_element. Do not pass a JSON string.",
            result={"elements": [], "count": 0},
        )

    ui_ops = get_ui_operations()
    lookup_hint = element_handle.get("lookup_hint") if isinstance(element_handle.get("lookup_hint"), dict) else {}
    bundle_name = element_handle.get("bundle_name") or lookup_hint.get("bundle_name")
    window_id = element_handle.get("window_id", lookup_hint.get("window_id"))

    raw = await asyncio.to_thread(
        ui_ops.find_element,
        device_id,
        element_id=element_handle.get("id"),
        element_type=element_handle.get("type"),
        bundle_name=bundle_name,
        window_id=window_id,
    )
    if not raw.get("success", False):
        return False, from_action_result(
            raw,
            default_code="FIND_ELEMENT_ERROR",
            default_detail="find element failed",
            default_result={"elements": [], "count": 0},
        )

    candidates = attach_element_metadata(
        raw.get("elements", []),
        bundle_name=bundle_name,
        window_id=raw.get("window_id", window_id),
        lookup_hint=lookup_hint,
    )
    matches = _match_handle_candidates(candidates, element_handle)
    if len(matches) == 1 and matches[0].get("x") is not None and matches[0].get("y") is not None:
        return True, _resolved_result(matches[0], resolved_via="handle", handle_refreshed=False)

    if not lookup_hint:
        return False, error_result(
            "ELEMENT_NOT_FOUND",
            "element_handle is stale and no lookup_hint is available for retry",
            result={"elements": [], "count": 0},
        )

    retry_raw = await asyncio.to_thread(
        ui_ops.find_element,
        device_id,
        text=lookup_hint.get("text"),
        element_type=lookup_hint.get("element_type"),
        element_id=lookup_hint.get("element_id"),
        bundle_name=lookup_hint.get("bundle_name"),
        window_id=lookup_hint.get("window_id"),
    )
    if not retry_raw.get("success", False):
        return False, from_action_result(
            retry_raw,
            default_code="FIND_ELEMENT_ERROR",
            default_detail="find element failed",
            default_result={"elements": [], "count": 0},
        )

    retry_candidates = attach_element_metadata(
        retry_raw.get("elements", []),
        bundle_name=lookup_hint.get("bundle_name"),
        window_id=retry_raw.get("window_id", lookup_hint.get("window_id")),
        lookup_hint=lookup_hint,
    )
    if len(retry_candidates) == 1 and retry_candidates[0].get("x") is not None and retry_candidates[0].get("y") is not None:
        return True, _resolved_result(retry_candidates[0], resolved_via="lookup_hint", handle_refreshed=True)

    if len(retry_candidates) > 1:
        return False, error_result(
            "AMBIGUOUS_ELEMENT_MATCH",
            "element_handle is stale and lookup_hint matched multiple elements; use a more specific text, element_id, or coordinates",
            result={
                "elements": retry_candidates,
                "count": len(retry_candidates),
                "match_count": len(retry_candidates),
                "candidate_handles": compact_candidate_handles(retry_candidates),
            },
        )

    return False, error_result(
        "ELEMENT_NOT_FOUND",
        "element_handle is stale and lookup_hint retry did not find the target element",
        result={"elements": [], "count": 0},
    )


async def _resolve_element_coords(
    device_id: str,
    text: Optional[str] = None,
    element_type: Optional[str] = None,
    element_id: Optional[str] = None,
    bundle_name: Optional[str] = None,
    window_id: Optional[int] = None,
) -> Tuple[bool, Union[Tuple[int, int], dict]]:
    ui_ops = get_ui_operations()
    raw = await asyncio.to_thread(
        ui_ops.find_element,
        device_id,
        text=text,
        element_type=element_type,
        element_id=element_id,
        bundle_name=bundle_name,
        window_id=window_id,
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
            f"element not found: text={text}, type={element_type}, id={element_id}",
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


async def _resolve_input_search_target(
    device_id: str,
    *,
    text: Optional[str],
    element_type: Optional[str],
    element_id: Optional[str],
    bundle_name: Optional[str],
) -> Tuple[bool, Dict[str, Any]]:
    """Resolve a search to one reusable handle so text input can be verified."""
    ui_ops = get_ui_operations()
    lookup_hint = build_lookup_hint(
        text=text,
        element_type=element_type,
        element_id=element_id,
        bundle_name=bundle_name,
    )
    raw = await asyncio.to_thread(
        ui_ops.find_element,
        device_id,
        text=text,
        element_type=element_type,
        element_id=element_id,
        bundle_name=bundle_name,
    )
    if not raw.get("success", False):
        return False, from_action_result(
            raw,
            default_code="FIND_ELEMENT_ERROR",
            default_detail="find element failed",
            default_result={"elements": [], "count": 0},
        )

    elements = attach_element_metadata(
        raw.get("elements", []),
        bundle_name=bundle_name,
        window_id=raw.get("window_id"),
        lookup_hint=lookup_hint,
    )
    if not elements:
        return False, error_result(
            "ELEMENT_NOT_FOUND",
            (
                "element not found for input_text lookup; call find_elements with "
                "more specific criteria and pass its element_handle"
            ),
            result={"elements": [], "count": 0},
        )
    if len(elements) > 1:
        return False, error_result(
            "AMBIGUOUS_ELEMENT_MATCH",
            "input_text search matched multiple elements; pass a specific element_handle",
            result={
                "elements": elements,
                "count": len(elements),
                "match_count": len(elements),
                "candidate_handles": compact_candidate_handles(elements),
            },
        )

    element = elements[0]
    if element.get("x") is None or element.get("y") is None:
        return False, error_result(
            "INVALID_ELEMENT_COORDS",
            f"invalid element coords: {element}",
            result={"elements": elements, "count": 1},
        )
    return True, _resolved_result(
        element,
        resolved_via="search",
        handle_refreshed=False,
    )


def _find_node_by_compid(nodes: List[Dict[str, Any]], compid: str) -> Optional[Dict[str, Any]]:
    """Find the first tree node whose ``properties.compid`` equals ``compid``."""
    for node in nodes:
        props = node.get("properties") or {}
        if props.get("compid") == compid:
            return node
        found = _find_node_by_compid(node.get("children") or [], compid)
        if found is not None:
            return found
    return None


def _collect_subtree_texts(node: Dict[str, Any]) -> List[str]:
    """Collect every non-empty ``text`` value in ``node`` and its descendants."""
    texts: List[str] = []
    props = node.get("properties") or {}
    text = props.get("text")
    if text:
        texts.append(text)
    for child in node.get("children") or []:
        texts.extend(_collect_subtree_texts(child))
    return texts


async def _read_subtree_input_text(
    device_id: str,
    active_handle: Dict[str, Any],
    expected_text: str,
    sentinel: Optional[str],
) -> Optional[str]:
    """Read the input value from the target element's subtree.

    Composite components (e.g. ``Search``) keep the editable text in a
    descendant node while the resolved element's own ``text`` stays empty.
    When the element's own text is empty, walk its subtree in the window UI
    tree and return the descendant text that holds the input value, so the
    success and sentinel-cleanup branches observe the real field value.
    """
    compid = active_handle.get("compid")
    window_id = active_handle.get("window_id")
    if not compid or window_id is None:
        return None
    hdc = get_hdc()
    raw = await asyncio.to_thread(hdc.get_ui_tree_raw, device_id, window_id)
    if not isinstance(raw, dict) or not raw.get("success", False):
        return None
    from harmonyos_dev_mcp.ui.tree_parser import UITreeParser

    parsed = UITreeParser().parse(raw.get("ui_tree") or "")
    if not isinstance(parsed, dict):
        return None
    target = _find_node_by_compid(parsed.get("nodes") or [], compid)
    if target is None:
        return None
    texts = _collect_subtree_texts(target)
    if not texts:
        return None
    sentinel_value = f"{expected_text}{sentinel}" if sentinel else None
    # Prefer exact matches so the existing success/cleanup branches fire.
    if expected_text in texts:
        return expected_text
    if sentinel_value and sentinel_value in texts:
        return sentinel_value
    # Otherwise report the deepest non-empty value so the timeout message
    # reflects what the field actually holds.
    return texts[-1]


async def _verify_input_handle(
    *,
    device_id: str,
    element_handle: Dict[str, Any],
    expected_text: str,
    sentinel: Optional[str],
    action_result: dict,
) -> dict:
    """Observe a handled input until it reaches a valid terminal text state."""
    loop = asyncio.get_running_loop()
    started = loop.time()
    timeout_ms = max(0, Config.INPUT_VERIFY_TIMEOUT_MS)
    deadline = started + timeout_ms / 1000
    result_data = dict(action_result.get("result") or {})
    active_handle = dict(element_handle)
    actual_text: Optional[str] = None
    observations = 0
    cleanup_pending = sentinel is not None
    cleanup_performed = False
    cleanup_blocked_by_focus = False
    last_resolution_error: Optional[dict] = None

    while loop.time() < deadline:
        verified_ok, verified = await _resolve_handle_coords(device_id, active_handle)
        observations += 1
        if loop.time() >= deadline:
            break
        if not verified_ok:
            last_resolution_error = verified
            continue

        verified_handle = dict(verified.get("element_handle") or {})
        if verified_handle:
            active_handle = verified_handle
        actual_text = active_handle.get("text")

        # Composite components (e.g. Search) keep the editable value in a
        # descendant node while the resolved element's own text stays empty.
        # Fall back to the subtree so verification and sentinel cleanup
        # observe the real field value instead of the empty parent.
        if actual_text != expected_text and not actual_text:
            subtree_text = await _read_subtree_input_text(
                device_id, active_handle, expected_text, sentinel
            )
            if subtree_text is not None:
                actual_text = subtree_text

        if actual_text == expected_text:
            result_data.update(
                {
                    "actual_text": actual_text,
                    "verified": True,
                    "element_handle": active_handle,
                    "cleanup_performed": cleanup_performed,
                    "observations": observations,
                    "elapsed_ms": int((loop.time() - started) * 1000),
                    "stage": "complete",
                    "message": "input text verified",
                }
            )
            action_result["result"] = result_data
            return action_result

        if cleanup_pending and actual_text == f"{expected_text}{sentinel}":
            cleanup_window_state = await _read_foreground_window_state(
                device_id,
                active_handle.get("window_id"),
            )
            if (
                active_handle.get("focused") is not True
                or cleanup_window_state.get("window_foreground") is not True
            ):
                cleanup_blocked_by_focus = True
                continue
            cleanup_raw = await asyncio.to_thread(
                get_ui_operations().press_key,
                device_id,
                int(KeyCode.DEL),
            )
            if not cleanup_raw.get("success", False):
                result_data.update(
                    {
                        "actual_text": actual_text,
                        "verified": False,
                        "element_handle": active_handle,
                        "cleanup_performed": False,
                        "observations": observations,
                        "elapsed_ms": int((loop.time() - started) * 1000),
                        "stage": "cleanup",
                    }
                )
                return error_result(
                    "TEXT_CLEANUP_FAILED",
                    "sentinel was observed, but Backspace could not remove it",
                    result=result_data,
                )
            cleanup_pending = False
            cleanup_performed = True

    result_data.update(
        {
            "actual_text": actual_text,
            "verified": False,
            "element_handle": active_handle,
            "cleanup_performed": cleanup_performed,
            "observations": observations,
            "elapsed_ms": int((loop.time() - started) * 1000),
            "stage": "observe",
        }
    )
    detail = (
        f"input was dispatched, but UI text did not become {expected_text!r} "
        f"within {timeout_ms}ms; last value was {actual_text!r}"
    )
    if cleanup_blocked_by_focus:
        detail = (
            "the sentinel-bearing value was observed, but cleanup was not dispatched "
            "because the target no longer had verified foreground focus"
        )
    if observations and last_resolution_error and actual_text is None:
        detail = "input was dispatched, but the target element could not be re-read before the verification deadline"
    return error_result(
        "TEXT_VERIFICATION_TIMEOUT",
        detail,
        result=result_data,
    )


@mcp_tool(category="ui")
@mcp_response("click")
@DeviceToolSupport.handle_tool_error("CLICK_ERROR", x=0, y=0)
@DeviceToolSupport.with_device(x=0, y=0)
@_serialize_ui_mutation
async def click(
    device_id: Optional[str] = None,
    x: Optional[int] = None,
    y: Optional[int] = None,
    element_handle: Optional[Dict[str, Any]] = None,
    text: Optional[str] = None,
    element_type: Optional[str] = None,
    element_id: Optional[str] = None,
    count: Literal[1, 2] = 1,
    bundle_name: Optional[str] = None,
) -> ClickResult:
    """
    Dispatch one or two clicks to a UI target.

    ``dispatched=true`` confirms command delivery. ``effect_verified`` remains
    false because a generic click cannot prove an application-level outcome.
    """
    has_coords = x is not None and y is not None
    has_handle = element_handle is not None
    has_search = bool(text or element_type or element_id)

    if count not in {1, 2}:
        return error_result(
            "INVALID_CLICK_COUNT",
            "count must be 1 or 2",
            result={"x": x or 0, "y": y or 0, "count": count},
        )

    if has_coords and (has_handle or has_search):
        return error_result(
            "PARAM_CONFLICT",
            "cannot provide coordinates together with element_handle or search criteria",
            result={"x": x, "y": y},
        )

    ui_ops = get_ui_operations()
    click_fn = ui_ops.double_click if count == 2 else ui_ops.click
    dispatch_message = "double click dispatched" if count == 2 else "click dispatched"

    if has_coords:
        return await _perform_unverified_action(
            action_fn=click_fn,
            device_id=device_id,
            resolved={
                "x": x,
                "y": y,
                "resolved_via": "coordinates",
                "handle_refreshed": False,
                "element_handle": None,
            },
            success_message=dispatch_message,
            dispatch_message=dispatch_message,
            default_code="CLICK_ERROR",
            default_detail="click failed",
            extra_result={"count": count},
        )

    if has_handle:
        ok, resolved = await _resolve_handle_coords(device_id, element_handle)
        if not ok:
            return resolved
        return await _perform_unverified_action(
            action_fn=click_fn,
            device_id=device_id,
            resolved=resolved,
            success_message=dispatch_message,
            dispatch_message=dispatch_message,
            default_code="CLICK_ERROR",
            default_detail="click failed",
            extra_result={"count": count},
        )

    if has_search:
        ok, coords = await _resolve_element_coords(
            device_id,
            text=text,
            element_type=element_type,
            element_id=element_id,
            bundle_name=bundle_name,
        )
        if not ok:
            return coords
        ex, ey = coords
        return await _perform_unverified_action(
            action_fn=click_fn,
            device_id=device_id,
            resolved={
                "x": ex,
                "y": ey,
                "resolved_via": "search",
                "handle_refreshed": False,
                "element_handle": None,
            },
            success_message=dispatch_message,
            dispatch_message=dispatch_message,
            default_code="CLICK_ERROR",
            default_detail="click failed",
            extra_result={"count": count},
        )

    return error_result(
        "MISSING_PARAMS",
        "must provide (x,y), element_handle, or (text/element_type)",
        result={"x": x or 0, "y": y or 0},
    )


@mcp_tool(category="ui")
@mcp_response("long_press")
@DeviceToolSupport.handle_tool_error("LONG_PRESS_ERROR")
@DeviceToolSupport.with_device()
@_serialize_ui_mutation
async def long_press(
    device_id: Optional[str] = None,
    x: Optional[int] = None,
    y: Optional[int] = None,
    element_handle: Optional[Dict[str, Any]] = None,
    text: Optional[str] = None,
    element_type: Optional[str] = None,
    element_id: Optional[str] = None,
    bundle_name: Optional[str] = None,
) -> LongPressResult:
    """
    Dispatch a long press to a UI target.

    ``dispatched=true`` confirms command delivery. ``effect_verified`` remains
    false because a generic long press cannot prove an application-level outcome.
    """
    ui_ops = get_ui_operations()

    if x is not None and y is not None and (element_handle is not None or text or element_type or element_id):
        return error_result(
            "PARAM_CONFLICT",
            "cannot provide coordinates together with element_handle or search criteria",
            result={"x": x, "y": y},
        )

    if x is not None and y is not None:
        return await _perform_unverified_action(
            action_fn=ui_ops.long_click,
            device_id=device_id,
            resolved={
                "x": x,
                "y": y,
                "resolved_via": "coordinates",
                "handle_refreshed": False,
                "element_handle": None,
            },
            success_message="long press dispatched",
            dispatch_message="long press dispatched",
            default_code="LONG_PRESS_ERROR",
            default_detail="long press failed",
        )

    if element_handle is not None:
        ok, resolved = await _resolve_handle_coords(device_id, element_handle)
        if not ok:
            return resolved
        return await _perform_unverified_action(
            action_fn=ui_ops.long_click,
            device_id=device_id,
            resolved=resolved,
            success_message="long press dispatched",
            dispatch_message="long press dispatched",
            default_code="LONG_PRESS_ERROR",
            default_detail="long press failed",
        )

    if text or element_type or element_id:
        ok, coords = await _resolve_element_coords(
            device_id,
            text=text,
            element_type=element_type,
            element_id=element_id,
            bundle_name=bundle_name,
        )
        if not ok:
            return coords
        ex, ey = coords
        return await _perform_unverified_action(
            action_fn=ui_ops.long_click,
            device_id=device_id,
            resolved={
                "x": ex,
                "y": ey,
                "resolved_via": "search",
                "handle_refreshed": False,
                "element_handle": None,
            },
            success_message="long press dispatched",
            dispatch_message="long press dispatched",
            default_code="LONG_PRESS_ERROR",
            default_detail="long press failed",
        )

    return error_result(
        "MISSING_PARAMS",
        "must provide coordinates, element_handle, or search criteria",
        result={"x": 0, "y": 0},
    )


@mcp_tool(category="ui")
@mcp_response("swipe")
@DeviceToolSupport.handle_tool_error("SWIPE_ERROR", from_x=0, from_y=0, to_x=0, to_y=0, direction=None)
@DeviceToolSupport.with_device(from_x=0, from_y=0, to_x=0, to_y=0, direction=None)
@_serialize_ui_mutation
async def swipe(
    device_id: Optional[str] = None,
    from_x: Optional[int] = None,
    from_y: Optional[int] = None,
    to_x: Optional[int] = None,
    to_y: Optional[int] = None,
    direction: Optional[str] = None,
    speed: int = 600,
) -> SwipeResult:
    """Swipe by direction or explicit start and end coordinates."""
    default_result = {
        "from_x": from_x or 0,
        "from_y": from_y or 0,
        "to_x": to_x or 0,
        "to_y": to_y or 0,
        "direction": direction,
    }

    ui_ops = get_ui_operations()

    if direction and any(v is not None for v in [from_x, from_y, to_x, to_y]):
        return error_result(
            "PARAM_CONFLICT",
            "cannot provide direction together with explicit swipe coordinates",
            result=default_result,
        )

    if direction:
        raw = await asyncio.to_thread(ui_ops.swipe_direction, device_id, direction, speed)
        raw = _with_success_message(raw, "swipe succeeded")
        return from_action_result(
            raw,
            default_code="SWIPE_ERROR",
            default_detail="swipe failed",
            default_result=default_result,
        )

    if all(v is not None for v in [from_x, from_y, to_x, to_y]):
        raw = await asyncio.to_thread(ui_ops.swipe, device_id, from_x, from_y, to_x, to_y, speed)
        raw = _with_success_message(raw, "swipe succeeded")
        return from_action_result(
            raw,
            default_code="SWIPE_ERROR",
            default_detail="swipe failed",
            default_result=default_result,
        )

    return error_result("MISSING_PARAMS", "must provide swipe coords or direction", result=default_result)


@mcp_tool(category="ui")
@mcp_response("input_text")
@DeviceToolSupport.handle_tool_error("INPUT_TEXT_ERROR", text="", x=0, y=0)
@DeviceToolSupport.with_device(text="", x=0, y=0)
@_serialize_ui_mutation
async def input_text(
    text: str,
    device_id: Optional[str] = None,
    x: Optional[int] = None,
    y: Optional[int] = None,
    element_handle: Optional[Dict[str, Any]] = None,
    element_text: Optional[str] = None,
    element_type: Optional[str] = None,
    element_id: Optional[str] = None,
    bundle_name: Optional[str] = None,
    mode: Literal["replace", "append"] = "replace",
) -> InputTextResult:
    """
    Set an input field to UTF-8 text, or append at the end when mode is ``append``.

    For reliable automation, first call find_elements/wait_for_element and pass its
    element_handle. Handle and unique-search modes verify foreground focus before
    dispatching text, then re-read the field and verify the exact final value.
    Coordinates cannot be re-read and therefore remain best-effort with
    verified=false. Replace mode is the default, and an empty replacement clears
    the field.
    """

    default_result = {
        "text": text or "",
        "requested_text": text or "",
        "x": x or 0,
        "y": y or 0,
        "mode": mode,
        "dispatched": False,
        "verified": False,
        "focus_dispatched": False,
        "focus_verified": False,
        "focus_observations": 0,
        "focused": None,
        "window_foreground": None,
        "foreground_window_id": None,
    }

    if text is None:
        return error_result("MISSING_TEXT", "text is required", result=default_result)
    if mode not in {"append", "replace"}:
        return error_result(
            "INVALID_MODE",
            "mode must be 'append' or 'replace'",
            result=default_result,
        )
    if mode == "append" and text == "":
        return error_result(
            "MISSING_TEXT",
            "text must not be empty in append mode; use replace mode to clear a field",
            result=default_result,
        )

    strategy, dispatched_text, clipboard_modified, sentinel = _input_strategy(text)
    default_result.update(
        {
            "input_strategy": strategy,
            "clipboard_modified": clipboard_modified,
        }
    )
    ui_ops = get_ui_operations()
    action_fn = ui_ops.input_text if mode == "append" else ui_ops.replace_text

    if x is not None and y is not None and (element_handle is not None or element_text or element_type or element_id):
        return error_result(
            "PARAM_CONFLICT",
            "cannot provide coordinates together with element_handle or search criteria",
            result=default_result,
        )

    if x is not None and y is not None:
        coordinate_strategy = strategy
        coordinate_text = dispatched_text
        coordinate_clipboard_modified = clipboard_modified
        if sentinel is not None:
            coordinate_strategy = "best_effort_direct"
            coordinate_text = text
            coordinate_clipboard_modified = False
        coordinate_result = {
            **default_result,
            "input_strategy": coordinate_strategy,
            "clipboard_modified": coordinate_clipboard_modified,
        }
        action_result = await _perform_resolved_action(
            action_fn=action_fn,
            device_id=device_id,
            resolved={
                "text": text,
                "x": x,
                "y": y,
                "resolved_via": "coordinates",
                "handle_refreshed": False,
                "element_handle": None,
                "mode": mode,
            },
            success_message="input text dispatched",
            default_code="INPUT_TEXT_ERROR",
            default_detail="input text failed",
            extra_args=(coordinate_text,),
            extra_result=coordinate_result,
        )
        result_data = dict(action_result.get("result") or {})
        result_data.update(
            {
                **coordinate_result,
                "x": x,
                "y": y,
                "resolved_via": "coordinates",
                "handle_refreshed": False,
                "element_handle": None,
                "dispatched": action_result.get("ok", False),
                "verified": False,
                "stage": "dispatched" if action_result.get("ok", False) else result_data.get("stage", "dispatch"),
                "message": (
                    "input text dispatched without verification"
                    if action_result.get("ok", False)
                    else result_data.get("message", "input text dispatch failed")
                ),
            }
        )
        action_result["result"] = result_data
        return action_result

    resolved: Optional[Dict[str, Any]] = None
    if element_handle is not None:
        ok, resolved = await _resolve_handle_coords(device_id, element_handle)
        if not ok:
            return resolved
    elif element_text or element_type or element_id:
        ok, resolved = await _resolve_input_search_target(
            device_id,
            text=element_text,
            element_type=element_type,
            element_id=element_id,
            bundle_name=bundle_name,
        )
        if not ok:
            return resolved
    else:
        return error_result(
            "MISSING_PARAMS",
            "must provide coordinates, element_handle, or search criteria",
            result=default_result,
        )

    assert resolved is not None
    focus_ok, focus_result = await _acquire_input_focus(
        device_id=device_id,
        resolved=resolved,
        default_result=default_result,
    )
    if not focus_ok:
        return focus_result

    resolved = {
        **resolved,
        **focus_result,
    }
    resolved_handle = dict(resolved.get("element_handle") or {})
    before_text = resolved_handle.get("text")
    if mode == "append" and not isinstance(before_text, str):
        return error_result(
            "TEXT_NOT_READABLE",
            "append mode requires a readable element text value so the final value can be verified",
            result={
                **default_result,
                **resolved,
                "before_text": before_text,
                "stage": "resolve_target",
            },
        )
    expected_text = text if mode == "replace" else f"{before_text}{text}"
    focused_action_fn = (
        ui_ops.input_focused_text
        if mode == "append"
        else ui_ops.replace_focused_text
    )

    action_result = await _perform_resolved_action(
        action_fn=focused_action_fn,
        device_id=device_id,
        resolved=resolved,
        success_message="input text dispatched",
        default_code="INPUT_TEXT_ERROR",
        default_detail="input text dispatch failed",
        extra_args=(dispatched_text,),
        extra_result={
            **default_result,
            "before_text": before_text,
            "actual_text": before_text,
            "stage": "dispatch",
        },
    )
    result_data = dict(action_result.get("result") or {})
    result_data.update(
        {
            **default_result,
            **resolved,
            "before_text": before_text,
            "actual_text": before_text,
            "dispatched": action_result.get("ok", False),
            "verified": False,
            "stage": result_data.get("stage", "dispatch"),
        }
    )
    action_result["result"] = result_data
    if not action_result.get("ok", False):
        return action_result

    return await _verify_input_handle(
        device_id=device_id,
        element_handle=resolved_handle,
        expected_text=expected_text,
        sentinel=sentinel,
        action_result=action_result,
    )


@mcp_tool(category="ui")
@mcp_response("press_key")
@DeviceToolSupport.handle_tool_error(
    "PRESS_KEY_ERROR",
    key=None,
    key_code=None,
    modifiers=[],
    event_key_codes=[],
    dispatched=False,
    effect_verified=False,
)
@DeviceToolSupport.with_device(
    key=None,
    key_code=None,
    modifiers=[],
    event_key_codes=[],
    dispatched=False,
    effect_verified=False,
)
@_serialize_ui_mutation
async def press_key(
    key: Union[str, int],
    modifiers: Optional[List[Literal["Ctrl", "Alt", "Shift", "Meta"]]] = None,
    device_id: Optional[str] = None,
) -> PressKeyResult:
    """
    Press one logical key, optionally with Ctrl, Alt, Shift, or Meta modifiers.

    Use ``input_text`` to enter strings. Use this tool for system keys and
    shortcuts such as key="Home" or key="V", modifiers=["Ctrl"]. ``key`` accepts
    every official HarmonyOS ``KEYCODE_*`` name and numeric value. Names are
    case- and separator-insensitive: ``Tab``, ``KEYCODE_TAB``, ``page-up``, and
    ``page_up`` are valid. Use ``Backspace`` for KEYCODE_DEL and ``Delete`` for
    KEYCODE_FORWARD_DEL. The result returns the canonical key name, its numeric
    code, and the exact key codes sent in the single HarmonyOS keyEvent.
    ``dispatched=true`` confirms command delivery; ``effect_verified`` remains
    false because arbitrary application behavior cannot be inferred from a key.
    """

    resolved_key = resolve_key(key)
    if resolved_key is None:
        return error_result(
            "INVALID_KEY",
            (
                f"unsupported key: {key}. Use any official HarmonyOS KEYCODE_* "
                "name (case and separators are optional) or its numeric value"
            ),
            result=_press_key_result(None),
        )

    requested_modifiers = list(modifiers or [])
    if len(requested_modifiers) > 2:
        return error_result(
            "INVALID_MODIFIER_COUNT",
            "HarmonyOS keyEvent supports at most two modifiers with one primary key",
            result=_press_key_result(resolved_key, modifiers=requested_modifiers),
        )

    normalized_modifiers: List[str] = []
    modifier_codes: List[int] = []
    for requested_modifier in requested_modifiers:
        resolved_modifier = _resolve_modifier(requested_modifier)
        if resolved_modifier is None:
            return error_result(
                "INVALID_MODIFIER",
                f"unsupported modifier: {requested_modifier}. Use Ctrl, Alt, Shift, or Meta",
                result=_press_key_result(resolved_key, modifiers=requested_modifiers),
            )
        modifier_name, modifier_code = resolved_modifier
        if modifier_name in normalized_modifiers:
            return error_result(
                "DUPLICATE_MODIFIER",
                f"modifier {modifier_name} was provided more than once",
                result=_press_key_result(resolved_key, modifiers=requested_modifiers),
            )
        normalized_modifiers.append(modifier_name)
        modifier_codes.append(modifier_code)

    if resolved_key.code in modifier_codes:
        return error_result(
            "DUPLICATE_MODIFIER",
            "the primary key duplicates one of the modifiers",
            result=_press_key_result(resolved_key, modifiers=normalized_modifiers),
        )

    event_key_codes = [*modifier_codes, resolved_key.code]
    ui_ops = get_ui_operations()
    if modifier_codes:
        raw = await asyncio.to_thread(ui_ops.send_key_event, device_id, event_key_codes)
    else:
        raw = await asyncio.to_thread(ui_ops.press_key, device_id, resolved_key.code)
    if isinstance(raw, dict):
        raw = dict(raw)
        raw.pop("key", None)
        raw.pop("keys", None)
        raw.pop("action", None)
        raw.update(
            _press_key_result(
                resolved_key,
                modifiers=normalized_modifiers,
                event_key_codes=event_key_codes,
                dispatched=raw.get("success", False),
            )
        )
    raw = _with_success_message(raw, "key event dispatched")
    return from_action_result(
        raw,
        default_code="PRESS_KEY_ERROR",
        default_detail="key event dispatch failed",
        default_result=_press_key_result(
            resolved_key,
            modifiers=normalized_modifiers,
            event_key_codes=event_key_codes,
        ),
    )


@mcp_tool(category="ui")
@mcp_response("find_elements")
@DeviceToolSupport.handle_tool_error("FIND_ELEMENT_ERROR", elements=[], count=0)
@DeviceToolSupport.with_device(elements=[], count=0)
async def find_elements(
    device_id: Optional[str] = None,
    text: Optional[str] = None,
    element_type: Optional[str] = None,
    element_id: Optional[str] = None,
    bundle_name: Optional[str] = None,
    window_id: Optional[int] = None,
) -> FindElementsResult:
    """Find UI elements and return reusable element handles."""
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
        window_id=window_id,
    )
    lookup_hint = build_lookup_hint(
        text=text,
        element_type=element_type,
        element_id=element_id,
        bundle_name=bundle_name,
        window_id=raw.get("window_id", window_id),
    )
    elements = attach_element_metadata(
        raw.get("elements", []),
        bundle_name=bundle_name,
        window_id=raw.get("window_id", window_id),
        lookup_hint=lookup_hint,
    )
    base = {"elements": elements, "count": raw.get("count", len(elements))}
    if raw.get("success", False) and base["count"] == 0:
        return error_result(
            "ELEMENT_NOT_FOUND",
            f"element not found: text={text}, type={element_type}, id={element_id}",
            result=base,
        )
    if isinstance(raw, dict):
        raw = dict(raw)
        raw["elements"] = elements
        raw["count"] = base["count"]
    return from_action_result(
        raw,
        default_code="FIND_ELEMENT_ERROR",
        default_detail="find element failed",
        default_result=base,
    )


@mcp_tool(category="ui")
@mcp_response("screenshot")
@DeviceToolSupport.handle_tool_error("SCREENSHOT_ERROR")
@DeviceToolSupport.with_device()
@DeviceToolSupport.validate_params(local_path=["path"])
async def screenshot(
    device_id: Optional[str] = None,
    local_path: Optional[str] = None,
    display_id: int = 0,
    left: Optional[int] = None,
    top: Optional[int] = None,
    right: Optional[int] = None,
    bottom: Optional[int] = None,
) -> ScreenshotResult:
    """Capture the full display or a rectangular screen region."""
    hdc = get_hdc()

    has_partial_bounds = any(v is not None for v in [left, top, right, bottom]) and not all(
        v is not None for v in [left, top, right, bottom]
    )
    if has_partial_bounds:
        return error_result(
            "PARAM_CONFLICT",
            "left, top, right, and bottom must all be provided together for region screenshots",
            result={"bounds": {"left": left, "top": top, "right": right, "bottom": bottom}},
        )

    if not local_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshots_dir = os.path.join(os.path.expanduser("~"), "harmonyos-screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)
        suffix = "element" if left is not None else "screenshot"
        local_path = os.path.join(screenshots_dir, f"{suffix}_{timestamp}.jpeg")

    if left is not None and top is not None and right is not None and bottom is not None:
        bounds = {"left": left, "top": top, "right": right, "bottom": bottom}
        raw = await asyncio.to_thread(hdc.take_element_screenshot, device_id, local_path, bounds)
        raw = _with_success_message(raw, "element screenshot succeeded")
        return from_action_result(
            raw,
            default_code="SCREENSHOT_ERROR",
            default_detail="element screenshot failed",
            default_result={"bounds": bounds},
        )

    raw = await asyncio.to_thread(hdc.take_screenshot, device_id, local_path, display_id)
    raw = _with_success_message(raw, "screenshot succeeded")
    return from_action_result(
        raw,
        default_code="SCREENSHOT_ERROR",
        default_detail="screenshot failed",
    )


@mcp_tool(category="ui")
@mcp_response("drag")
@DeviceToolSupport.handle_tool_error("DRAG_ERROR")
@DeviceToolSupport.with_device()
@_serialize_ui_mutation
async def drag(
    device_id: Optional[str] = None,
    from_x: Optional[int] = None,
    from_y: Optional[int] = None,
    to_x: Optional[int] = None,
    to_y: Optional[int] = None,
    speed: int = 600,
) -> DragResult:
    """Drag from one screen coordinate to another."""
    if not all(v is not None for v in [from_x, from_y, to_x, to_y]):
        return error_result(
            "MISSING_PARAMS",
            "must provide from_x, from_y, to_x, to_y",
            result={"from_x": from_x or 0, "from_y": from_y or 0, "to_x": to_x or 0, "to_y": to_y or 0},
        )

    ui_ops = get_ui_operations()
    raw = await asyncio.to_thread(ui_ops.drag, device_id, from_x, from_y, to_x, to_y, speed)
    raw = _with_success_message(raw, "drag succeeded")
    if isinstance(raw, dict):
        raw.pop("from", None)
        raw.pop("to", None)
    return from_action_result(
        raw,
        default_code="DRAG_ERROR",
        default_detail="drag failed",
        default_result={"from_x": from_x, "from_y": from_y, "to_x": to_x, "to_y": to_y},
    )
