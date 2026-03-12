"""Shared payload normalizers for HarmonyOS MCP tools."""

from .element import attach_element_metadata, build_lookup_hint, compact_candidate_handles, normalize_element
from .window import normalize_window, normalize_windows

__all__ = [
    "attach_element_metadata",
    "build_lookup_hint",
    "compact_candidate_handles",
    "normalize_element",
    "normalize_window",
    "normalize_windows",
]
