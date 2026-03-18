"""Window payload normalization helpers."""

from __future__ import annotations

from typing import Any, Dict

from ..ui_common import normalize_bundle_name, rect_to_bounds


def normalize_window(window: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(window)
    bundle_name = normalized.get("bundle_name")
    normalized["bundle_name"] = bundle_name if isinstance(bundle_name, str) else ""
    normalized["bundle_name_resolved"] = bool(normalize_bundle_name(normalized.get("bundle_name")))
    normalized.setdefault("is_visible", False)
    normalized["bounds"] = rect_to_bounds(normalized.get("rect"))
    return normalized


def normalize_windows(windows: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    return [normalize_window(window) for window in windows]
