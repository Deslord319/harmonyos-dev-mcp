"""MCP server factory and runtime helpers."""

from __future__ import annotations

import inspect
from functools import wraps
from typing import Callable, List, Optional
from datetime import datetime, timezone

from fastmcp import FastMCP
from loguru import logger

from common.exceptions import MCPError
from common.tools.registry import get_registered_tools, get_tool_summary


def create_server(
    name: str,
    tool_modules: Optional[List] = None,
    enable_error_handler: bool = True,
    on_error: Optional[Callable] = None,
) -> FastMCP:
    """Create FastMCP server and register all discovered tools."""
    server = FastMCP(name)

    # Import-only side effects are still allowed for explicit tool registration.
    if tool_modules:
        for _module in tool_modules:
            pass

    server._tools = {}
    for entry in get_registered_tools():
        func = entry.func
        if enable_error_handler:
            func = _wrap_with_error_handler(func, on_error)
        server.tool()(func)
        server._tools[func.__name__] = func

    summary = get_tool_summary()
    logger.info(f"Registered {summary['total']} tools, categories: {summary['categories']}")
    return server


def _extract_error_info(result: dict) -> Optional[tuple[str, str]]:
    """Extract error message/code from MCP standard envelope only."""
    structured = result
    if isinstance(result.get("structuredContent"), dict):
        structured = result["structuredContent"]

    # Strict mode: only accept MCP-standard fields.
    if "ok" not in structured:
        return None
    if structured.get("ok", True):
        return None

    error_obj = structured.get("error")
    if not isinstance(error_obj, dict):
        return ("Unknown error", "UNKNOWN")

    error_msg = str(error_obj.get("detail") or "Unknown error")
    error_code = str(error_obj.get("code") or "UNKNOWN")
    return error_msg, error_code


def _error_result(tool_name: str, code: str, detail: str) -> dict:
    return {
        "content": [{"type": "text", "text": f"{tool_name}: {detail}"}],
        "structuredContent": {
            "tool": tool_name,
            "ok": False,
            "result": None,
            "error": {
                "code": code,
                "detail": detail,
            },
            "meta": {
                "request_id": "server-error",
                "duration_ms": 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        },
        "isError": True,
    }


def _wrap_with_error_handler(func, on_error: Optional[Callable] = None):
    """Wrap sync/async tool functions with unified error handling."""

    if inspect.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                if isinstance(result, dict):
                    error_info = _extract_error_info(result)
                    if error_info:
                        error_msg, error_code = error_info
                        logger.error(f"Tool {func.__name__} failed [{error_code}]: {error_msg}")
                        if on_error:
                            on_error(error_msg, error_code)
                return result
            except MCPError as e:
                logger.error(f"Tool {func.__name__} MCP error [{e.code}]: {e.message}")
                if on_error:
                    on_error(e.message, e.code)
                return _error_result(func.__name__, e.code, e.message)
            except Exception as e:
                logger.exception(f"Tool {func.__name__} unexpected error: {e}")
                if on_error:
                    on_error(str(e), "UNEXPECTED_ERROR")
                return _error_result(func.__name__, "UNEXPECTED_ERROR", str(e))

        return async_wrapper

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            if isinstance(result, dict):
                error_info = _extract_error_info(result)
                if error_info:
                    error_msg, error_code = error_info
                    logger.error(f"Tool {func.__name__} failed [{error_code}]: {error_msg}")
                    if on_error:
                        on_error(error_msg, error_code)
            return result
        except MCPError as e:
            logger.error(f"Tool {func.__name__} MCP error [{e.code}]: {e.message}")
            if on_error:
                on_error(e.message, e.code)
            return _error_result(func.__name__, e.code, e.message)
        except Exception as e:
            logger.exception(f"Tool {func.__name__} unexpected error: {e}")
            if on_error:
                on_error(str(e), "UNEXPECTED_ERROR")
            return _error_result(func.__name__, "UNEXPECTED_ERROR", str(e))

    return wrapper


def run_server(
    server: FastMCP,
    config_class=None,
    setup_logger_func: Optional[Callable] = None,
    on_startup: Optional[Callable] = None,
    on_error: Optional[Callable] = None,
):
    """Run MCP server with optional bootstrap hooks."""
    if setup_logger_func:
        setup_logger_func()

    if config_class:
        config_class.ensure_init()

    if on_startup:
        try:
            on_startup()
        except Exception as e:
            logger.warning(f"Startup callback failed: {e}")
            if on_error:
                on_error(str(e), "STARTUP_ERROR")

    try:
        server.run()
    except KeyboardInterrupt:
        logger.info("Server stopped")
    except Exception as e:
        logger.exception(f"Server run exception: {e}")
        if on_error:
            on_error(str(e), "SERVER_RUN_ERROR")
        raise
