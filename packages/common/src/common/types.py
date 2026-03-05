from __future__ import annotations

"""Common response types for internal tool results and MCP envelopes."""

from typing import Any, TypedDict


class BaseResult(TypedDict, total=False):
    """Unified internal result schema."""

    tool: str
    ok: bool
    result: Any
    error: MCPError | None
    meta: MCPMeta


class MCPError(TypedDict, total=False):
    """Unified error object in structuredContent."""

    code: str
    detail: str


class MCPMeta(TypedDict, total=False):
    """Metadata fields for observability."""

    request_id: str
    duration_ms: int
    timestamp: str


class MCPStructuredContent(TypedDict, total=False):
    """Machine-readable MCP payload."""

    tool: str
    ok: bool
    result: Any
    error: MCPError | None
    meta: MCPMeta


class MCPResult(TypedDict, total=False):
    """Top-level MCP result returned to clients."""

    content: list[dict[str, Any]]
    structuredContent: MCPStructuredContent
    isError: bool
