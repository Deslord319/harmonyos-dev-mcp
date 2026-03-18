"""Element payload normalization helpers."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..ui_common import element_to_bounds


def build_lookup_hint(
    *,
    text: Optional[str] = None,
    element_type: Optional[str] = None,
    element_id: Optional[str] = None,
    bundle_name: Optional[str] = None,
    window_id: Optional[int] = None,
) -> Dict[str, Any]:
    hint: Dict[str, Any] = {}
    if text:
        hint["text"] = text
    if element_type:
        hint["element_type"] = element_type
    if element_id:
        hint["element_id"] = element_id
    if bundle_name:
        hint["bundle_name"] = bundle_name
    if window_id is not None:
        hint["window_id"] = window_id
    return hint


def normalize_element(
    element: Dict[str, Any],
    *,
    bundle_name: Optional[str],
    window_id: Optional[int],
    lookup_hint: Optional[Dict[str, Any]] = None,
    lookup_is_broad: Optional[bool] = None,
) -> Dict[str, Any]:
    normalized = dict(element)
    bounds = element_to_bounds(normalized)
    if bounds:
        normalized["bounds"] = bounds

    effective_window_id = normalized.get("window_id", window_id)
    handle = {
        "window_id": effective_window_id,
        "id": normalized.get("id"),
        "compid": normalized.get("compid"),
        "type": normalized.get("type"),
        "text": normalized.get("text"),
        "x": normalized.get("x"),
        "y": normalized.get("y"),
        "bounds": normalized.get("bounds"),
        "bundle_name": bundle_name,
    }
    if lookup_hint:
        handle["lookup_hint"] = dict(lookup_hint)
    normalized["element_handle"] = {k: v for k, v in handle.items() if v is not None}
    if lookup_is_broad is not None:
        normalized["lookup_is_broad"] = lookup_is_broad
    return normalized


def attach_element_metadata(
    elements: list[Dict[str, Any]],
    *,
    bundle_name: Optional[str],
    window_id: Optional[int],
    lookup_hint: Optional[Dict[str, Any]],
) -> list[Dict[str, Any]]:
    hint = lookup_hint or {}
    is_broad_lookup = bool(hint.get("element_type")) and not (hint.get("text") or hint.get("element_id"))
    lookup_is_broad = is_broad_lookup or len(elements) > 1
    return [
        normalize_element(
            element,
            bundle_name=bundle_name,
            window_id=window_id,
            lookup_hint=lookup_hint,
            lookup_is_broad=lookup_is_broad,
        )
        for element in elements
    ]


def compact_candidate_handles(elements: list[Dict[str, Any]], limit: int = 3) -> list[Dict[str, Any]]:
    compact = []
    for element in elements[:limit]:
        compact.append(
            {
                "id": element.get("id"),
                "compid": element.get("compid"),
                "type": element.get("type"),
                "text": element.get("text"),
                "x": element.get("x"),
                "y": element.get("y"),
            }
        )
    return compact
