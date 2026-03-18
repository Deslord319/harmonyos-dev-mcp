"""Shared UI/window normalization helpers."""

from typing import Any, Optional


def normalize_bundle_name(bundle_name: Optional[str]) -> str:
    return bundle_name.strip() if isinstance(bundle_name, str) else ""


def rect_to_bounds(rect: Optional[dict[str, Any]]) -> dict[str, int]:
    if not isinstance(rect, dict):
        return {"left": 0, "top": 0, "right": 0, "bottom": 0}
    x = int(rect.get("x", 0))
    y = int(rect.get("y", 0))
    w = int(rect.get("w", 0))
    h = int(rect.get("h", 0))
    return {"left": x, "top": y, "right": x + w, "bottom": y + h}


def element_to_bounds(element: dict[str, Any]) -> Optional[dict[str, int]]:
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
