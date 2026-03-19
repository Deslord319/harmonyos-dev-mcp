"""MCP server factory and runtime helpers."""

from __future__ import annotations

import inspect
from functools import wraps
from typing import Callable, Optional

from fastmcp import FastMCP
from loguru import logger

from common.exceptions import MCPError
from common.tools.registry import get_registered_tools, get_tool_summary
from common.tools.response import error_envelope, extract_error_info, to_mcp_result


def create_server(
    name: str,
    enable_error_handler: bool = True,
    on_error: Optional[Callable] = None,
) -> FastMCP:
    """Create FastMCP server and register all discovered tools."""
    server = FastMCP(name)
    registered_tools = []
    for entry in get_registered_tools():
        func = entry.func
        if enable_error_handler:
            func = _wrap_with_error_handler(func, on_error)
        server.tool(output_schema=None)(func)
        registered_tools.append(func)

    server.codex_registered_tools = tuple(registered_tools)

    summary = get_tool_summary()
    logger.info(f"Registered {summary['total']} tools, categories: {summary['categories']}")
    return server

def _error_result(tool_name: str, code: str, detail: str) -> dict:
    return to_mcp_result(
        error_envelope(
            tool=tool_name,
            code=code,
            detail=detail,
            request_id="server-error",
            duration_ms=0,
        )
    )


def _wrap_with_error_handler(func, on_error: Optional[Callable] = None):
    """Wrap sync/async tool functions with unified error handling."""

    if inspect.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                if isinstance(result, dict):
                    error_info = extract_error_info(result)
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
                error_info = extract_error_info(result)
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
    show_banner: bool = False,
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
        server.run(show_banner=show_banner)
    except KeyboardInterrupt:
        logger.info("Server stopped")
    except Exception as e:
        logger.exception(f"Server run exception: {e}")
        if on_error:
            on_error(str(e), "SERVER_RUN_ERROR")
        raise
