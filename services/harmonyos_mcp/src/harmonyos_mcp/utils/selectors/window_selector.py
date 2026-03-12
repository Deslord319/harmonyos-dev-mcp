"""Window target selection helpers."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..ui_common import normalize_bundle_name


def resolve_window_target(
    windows: list[Dict[str, Any]],
    *,
    bundle_name: Optional[str] = None,
    window_id: Optional[int] = None,
) -> Dict[str, Any]:
    if not windows:
        return {
            "success": False,
            "error_code": "NO_WINDOWS",
            "error": "no window found",
            "window": None,
            "windows": [],
        }

    target_bundle = normalize_bundle_name(bundle_name)
    matched_window: Optional[Dict[str, Any]] = None

    if window_id is not None:
        matched_window = next((w for w in windows if w.get("window_id") == window_id), None)
        if not matched_window:
            return {
                "success": False,
                "error_code": "WINDOW_NOT_FOUND",
                "error": f"window not found: {window_id}",
                "window": None,
                "windows": windows,
            }
        if target_bundle and normalize_bundle_name(matched_window.get("bundle_name")) != target_bundle:
            return {
                "success": False,
                "error_code": "WINDOW_BUNDLE_MISMATCH",
                "error": f"window {window_id} does not match bundle: {target_bundle}",
                "window": None,
                "windows": windows,
            }
        return {"success": True, "window": matched_window, "windows": windows}

    if target_bundle:
        visible_matches = [
            window
            for window in windows
            if window.get("is_visible") and normalize_bundle_name(window.get("bundle_name")) == target_bundle
        ]
        matched_window = visible_matches[0] if visible_matches else None
        if not matched_window:
            any_matches = [window for window in windows if normalize_bundle_name(window.get("bundle_name")) == target_bundle]
            matched_window = any_matches[0] if any_matches else None
        if not matched_window:
            return {
                "success": False,
                "error_code": "WINDOW_NOT_FOUND",
                "error": f"window not found for bundle: {target_bundle}",
                "window": None,
                "windows": windows,
            }
        return {"success": True, "window": matched_window, "windows": windows}

    for window in windows:
        if window.get("is_visible"):
            return {"success": True, "window": window, "windows": windows}
    return {"success": True, "window": windows[0], "windows": windows}
