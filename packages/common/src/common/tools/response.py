"""
Unified MCP response envelope for HarmonyOS MCP tools.

Provides decorators and helper functions to wrap tool outputs
into MCP-standard response format.
"""

from __future__ import annotations

import functools
import inspect
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict
from uuid import uuid4

from loguru import logger


def mcp_response(tool: str):
    """Wrap tool outputs to MCP-standard top-level result."""

    def decorator(func: Callable):
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                started = time.perf_counter()
                request_id = str(uuid4())
                try:
                    raw = await func(*args, **kwargs)
                    envelope = _normalize_result(
                        tool=tool,
                        raw=raw,
                        request_id=request_id,
                        duration_ms=_duration_ms(started),
                    )
                except Exception as e:  # pragma: no cover - safety net
                    logger.exception(f"Tool {tool} unexpected error: {e}")
                    envelope = _error_envelope(
                        tool=tool,
                        code="INTERNAL_ERROR",
                        detail=str(e),
                        request_id=request_id,
                        duration_ms=_duration_ms(started),
                    )
                return _to_mcp_result(envelope)

            return async_wrapper

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            started = time.perf_counter()
            request_id = str(uuid4())
            try:
                raw = func(*args, **kwargs)
                envelope = _normalize_result(
                    tool=tool,
                    raw=raw,
                    request_id=request_id,
                    duration_ms=_duration_ms(started),
                )
            except Exception as e:  # pragma: no cover - safety net
                logger.exception(f"Tool {tool} unexpected error: {e}")
                envelope = _error_envelope(
                    tool=tool,
                    code="INTERNAL_ERROR",
                    detail=str(e),
                    request_id=request_id,
                    duration_ms=_duration_ms(started),
                )
            return _to_mcp_result(envelope)

        return wrapper

    return decorator


def _duration_ms(started: float) -> int:
    return max(0, int((time.perf_counter() - started) * 1000))


def _to_mcp_result(envelope: Dict[str, Any]) -> Dict[str, Any]:
    if envelope["ok"]:
        text = f"{envelope['tool']}: ok"
    else:
        detail = envelope.get("error", {}).get("detail") or "Operation failed"
        text = f"{envelope['tool']}: {detail}"
    return {
        "content": [{"type": "text", "text": text}],
        "structuredContent": envelope,
        "isError": not envelope["ok"],
    }


def _normalize_result(tool: str, raw: Any, request_id: str, duration_ms: int) -> Dict[str, Any]:
    # Already full MCP-shaped.
    if isinstance(raw, dict) and {"content", "structuredContent", "isError"} <= set(raw.keys()):
        structured = raw.get("structuredContent", {})
        if isinstance(structured, dict):
            structured["meta"] = _merge_meta(structured.get("meta"), request_id, duration_ms)
        return structured

    # Already standardized structured envelope.
    if isinstance(raw, dict) and {"tool", "ok", "result", "error"} <= set(raw.keys()):
        envelope = dict(raw)
        envelope["tool"] = envelope.get("tool") or tool
        envelope["meta"] = _merge_meta(envelope.get("meta"), request_id, duration_ms)
        return envelope

    if not isinstance(raw, dict):
        return _ok_envelope(
            tool=tool,
            result=raw,
            request_id=request_id,
            duration_ms=duration_ms,
        )

    # Strict mode: decorated tools must return standardized envelope.
    return _error_envelope(
        tool=tool,
        code="INVALID_TOOL_RESULT_SCHEMA",
        detail=f"{tool} returned non-standard dict result",
        request_id=request_id,
        duration_ms=duration_ms,
    )


def _meta(request_id: str, duration_ms: int) -> Dict[str, Any]:
    return {
        "request_id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "duration_ms": duration_ms,
    }


def _merge_meta(existing: Any, request_id: str, duration_ms: int) -> Dict[str, Any]:
    base = _meta(request_id, duration_ms)
    if not isinstance(existing, dict):
        return base
    merged = dict(base)
    merged.update({k: v for k, v in existing.items() if v not in (None, "")})
    return merged


def _ok_envelope(tool: str, result: Any, request_id: str, duration_ms: int) -> Dict[str, Any]:
    return {
        "tool": tool,
        "ok": True,
        "result": result,
        "error": None,
        "meta": _meta(request_id, duration_ms),
    }


def ok_result(result: Any, tool: str = "") -> Dict[str, Any]:
    """Build standardized successful structuredContent."""
    return {
        "tool": tool,
        "ok": True,
        "result": result,
        "error": None,
        "meta": {},
    }


def error_result(
    code: str,
    detail: str,
    *,
    result: Any = None,
    tool: str = "",
) -> Dict[str, Any]:
    """Build standardized failed structuredContent."""
    return {
        "tool": tool,
        "ok": False,
        "result": result,
        "error": {
            "code": code,
            "detail": detail,
        },
        "meta": {},
    }


def from_action_result(
    raw: Any,
    *,
    default_code: str,
    default_detail: str,
    default_result: Any = None,
) -> Dict[str, Any]:
    """
    Normalize low-level action result (usually `success` based dict) into
    standardized `ok/result/error` envelope.
    """
    if isinstance(raw, dict) and "ok" in raw and "error" in raw:
        return raw

    if not isinstance(raw, dict):
        return ok_result(raw if raw is not None else default_result)

    if "success" not in raw:
        merged = (
            {}
            if default_result is None
            else (dict(default_result) if isinstance(default_result, dict) else default_result)
        )
        if isinstance(merged, dict):
            merged.update(raw)
            return ok_result(merged)
        return ok_result(raw)

    merged = (
        {}
        if default_result is None
        else (dict(default_result) if isinstance(default_result, dict) else default_result)
    )
    if isinstance(merged, dict):
        for k, v in raw.items():
            if k not in {"success", "error", "error_code", "hint", "retryable"}:
                merged[k] = v

    if raw.get("success", False):
        return ok_result(merged if isinstance(merged, dict) else raw)

    return error_result(
        raw.get("error_code", default_code),
        raw.get("error", default_detail),
        result=merged if isinstance(merged, dict) else default_result,
    )


def _error_envelope(
    tool: str,
    code: str,
    detail: str,
    request_id: str,
    duration_ms: int,
) -> Dict[str, Any]:
    return {
        "tool": tool,
        "ok": False,
        "result": None,
        "error": {
            "code": code,
            "detail": detail,
        },
        "meta": _meta(request_id, duration_ms),
    }
