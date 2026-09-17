"""
Pure Python MCP stdio server for HarmonyOS.

No dependency on fastmcp or mcp SDK — implements JSON-RPC 2.0 over stdio
using only Python standard library.

Usage:
  python3 -m harmonyos_dev_mcp.harmonyos.mcp_server

Environment variables:
  HDC_USE_TCP=1              # Enable TCP mode (required on HarmonyOS)
  HARMONYOS_HDC_SERVER=127.0.0.1:8710  # hdc server address
  HARMONYOS_SDK_PATH=...     # SDK path
  DEVECO_STUDIO_PATH=...    # DevEco path (can be empty on HarmonyOS)
"""

import asyncio
import inspect
import json
import os
import sys
import traceback
from typing import Any, Dict, List, Optional, get_args, get_origin

# --- Bootstrap: set up PYTHONPATH to include stubs + src ---

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.dirname(os.path.dirname(_HERE))  # src/ directory
_STUBS = os.path.join(_HERE, "stubs")

for _p in (_STUBS, _SRC):
    if _p not in sys.path:
        sys.path.insert(0, _p)


# --- Tool schema extraction ---

def _get_type_str(annotation: Any) -> str:
    """Convert Python type annotation to JSON Schema type string."""
    if annotation is inspect.Parameter.empty or annotation is Any:
        return "any"
    origin = get_origin(annotation)
    if origin is type(None):
        return ""
    # Optional[X] → Union[X, None]
    if hasattr(annotation, "__origin__") and annotation.__origin__ is type(Optional):
        pass
    try:
        import typing
        if origin is typing.Union:
            args = get_args(annotation)
            non_none = [a for a in args if a is not type(None)]
            if len(non_none) == 1:
                return _get_type_str(non_none[0])
            return "any"
    except Exception:
        pass
    if annotation is str:
        return "string"
    if annotation is int:
        return "integer"
    if annotation is bool:
        return "boolean"
    if annotation is float:
        return "number"
    if origin is list or annotation is list:
        return "array"
    if origin is dict or annotation is dict:
        return "object"
    # Literal types → string with enum
    try:
        import typing
        if hasattr(annotation, "__origin__") and annotation.__origin__ is typing.Literal:
            return "string"
    except Exception:
        pass
    return "any"


def _extract_schema(func) -> Dict[str, Any]:
    """Extract JSON Schema from function signature."""
    sig = inspect.signature(func)
    properties: Dict[str, Any] = {}
    required: List[str] = []

    for name, param in sig.parameters.items():
        if name in ("self",):
            continue
        ptype = _get_type_str(param.annotation)
        prop: Dict[str, Any] = {"type": ptype}

        if param.default is not inspect.Parameter.empty:
            prop["default"] = param.default
        else:
            required.append(name)

        # Literal types → enum
        try:
            import typing
            if hasattr(param.annotation, "__origin__") and param.annotation.__origin__ is typing.Literal:
                prop["enum"] = list(get_args(param.annotation))
        except Exception:
            pass

        properties[name] = prop

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def _get_description(func) -> str:
    """Get first non-empty line of docstring."""
    doc = func.__doc__ or ""
    for line in doc.strip().split("\n"):
        line = line.strip()
        if line:
            return line
    return func.__name__


def _serialize_result(result: Any) -> str:
    """Serialize tool result to text for MCP content."""
    # ToolResult objects (from our fastmcp stub)
    if hasattr(result, "structured_content") and result.structured_content is not None:
        sc = result.structured_content
        if isinstance(sc, dict):
            if "ok" in sc:
                if sc.get("ok"):
                    return json.dumps(sc.get("result", sc), ensure_ascii=False, default=str, indent=2)
                else:
                    err = sc.get("error", {})
                    return f"Error [{err.get('code', '')}]: {err.get('detail', '')}"
            return json.dumps(sc, ensure_ascii=False, default=str, indent=2)
    if hasattr(result, "content") and result.content is not None:
        return str(result.content)
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        return json.dumps(result, ensure_ascii=False, default=str, indent=2)
    try:
        return json.dumps(result, ensure_ascii=False, default=str, indent=2)
    except Exception:
        return str(result)


# --- Tool registration ---

def register_all_tools() -> Dict[str, Any]:
    """Import all tool functions and build the registry."""
    from harmonyos_dev_mcp.tools import build, e2e, general, ui
    from harmonyos_dev_mcp.tools.log.query import logs_query

    tool_funcs = {
        "build_app": build.build_app,
        "install_app": build.install_app,
        "run_app": build.run_app,
        "uninstall_app": build.uninstall_app,
        "list_devices": general.list_devices,
        "query_package": general.query_package,
        "get_ui_tree": e2e.get_ui_tree,
        "list_windows": e2e.list_windows,
        "wait_for_element": e2e.wait_for_element,
        "click": ui.click,
        "long_press": ui.long_press,
        "swipe": ui.swipe,
        "input_text": ui.input_text,
        "press_key": ui.press_key,
        "find_elements": ui.find_elements,
        "screenshot": ui.screenshot,
        "drag": ui.drag,
        "logs_query": logs_query,
    }

    registry: Dict[str, Any] = {}
    for name, func in tool_funcs.items():
        registry[name] = {
            "func": func,
            "name": name,
            "description": _get_description(func),
            "inputSchema": _extract_schema(func),
        }
        print(f"[mcp] registered: {name}", file=sys.stderr)

    return registry


def build_tools_list(registry: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build tools/list response."""
    return [
        {
            "name": info["name"],
            "description": info["description"],
            "inputSchema": info["inputSchema"],
        }
        for name, info in registry.items()
    ]


# --- JSON-RPC handler ---

async def handle_request(
    request: Dict[str, Any], registry: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Handle a JSON-RPC request, return response (or None for notifications)."""
    method = request.get("method", "")
    req_id = request.get("id")
    params = request.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "harmonyos-dev-mcp",
                    "version": "0.9.1",
                },
            },
        }

    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": build_tools_list(registry)},
        }

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if tool_name not in registry:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"Error: unknown tool '{tool_name}'"}],
                    "isError": True,
                },
            }

        func = registry[tool_name]["func"]
        try:
            if inspect.iscoroutinefunction(func):
                result = await func(**arguments)
            else:
                result = func(**arguments)

            text = _serialize_result(result)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": text}],
                    "isError": False,
                },
            }
        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
            print(f"[mcp] tool {tool_name} error: {e}", file=sys.stderr)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": error_msg}],
                    "isError": True,
                },
            }

    if req_id is not None:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }
    return None


# --- Main loop ---

def main():
    """Entry point: synchronous stdin reader + async tool dispatcher."""
    print("[mcp] Starting harmonyos-dev-mcp (HarmonyOS mode)...", file=sys.stderr)

    # Initialize config
    from harmonyos_dev_mcp.config import Config
    Config.ensure_init()

    # Register all tools
    registry = register_all_tools()
    print(f"[mcp] {len(registry)} tools registered, ready.", file=sys.stderr)

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                print("[mcp] stdin closed, exiting.", file=sys.stderr)
                break

            line_str = line.strip()
            if not line_str:
                continue

            try:
                request = json.loads(line_str)
            except json.JSONDecodeError as e:
                print(f"[mcp] JSON parse error: {e}", file=sys.stderr)
                continue

            response = asyncio.run(handle_request(request, registry))

            if response is not None:
                response_str = json.dumps(response, ensure_ascii=False)
                sys.stdout.write(response_str + "\n")
                sys.stdout.flush()

        except Exception as e:
            print(f"[mcp] error: {e}\n{traceback.format_exc()}", file=sys.stderr)
            continue


if __name__ == "__main__":
    main()
