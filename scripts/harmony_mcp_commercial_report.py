"""Run harmonyos_mcp tools and export a commercial-grade minimal report.

Default output schema keeps only:
- tool / ok / result / error / meta

Use --debug to include call arguments for troubleshooting.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable

from harmonyos_mcp.tools.build import build_app, install_app, run_app, uninstall_app
from harmonyos_mcp.tools.general import list_devices, query_package
from harmonyos_mcp.tools.log.query import logs_query
from harmonyos_mcp.tools.ui import (
    click_element,
    drag,
    find_element,
    input_text,
    long_press_element,
    press_key,
    screenshot,
    swipe,
)
from harmonyos_mcp.tools.ui_tree import get_ui_tree, list_windows


ToolFn = Callable[..., Awaitable[dict]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export commercial MCP report")
    parser.add_argument("--project-path", required=True, help="Harmony project path")
    parser.add_argument("--bundle-name", required=True, help="Bundle name to test")
    parser.add_argument(
        "--output",
        default=str(Path.home() / "Desktop"),
        help="Output directory for json report and screenshot",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Include call args in each tool record",
    )
    return parser.parse_args()


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _to_utc_z(ts: Any) -> str | None:
    if not isinstance(ts, str) or not ts:
        return None
    try:
        norm = ts.replace("Z", "+00:00")
        dt = datetime.fromisoformat(norm)
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except Exception:
        return ts


def _sanitize_result(tool: str | None, result: Any) -> Any:
    if not isinstance(result, dict):
        return result

    if tool == "list_windows":
        windows = result.get("windows") or []
        sample = []
        for win in windows[:5]:
            if isinstance(win, dict):
                sample.append(
                    {
                        "window_id": win.get("window_id"),
                        "window_name": win.get("window_name"),
                        "bundle_name": win.get("bundle_name"),
                        "is_visible": win.get("is_visible"),
                        "rect": win.get("rect"),
                    }
                )
        return {
            "count": len(windows),
            "visible_count": sum(1 for w in windows if isinstance(w, dict) and w.get("is_visible")),
            "sample_windows": sample,
        }

    if tool == "get_ui_tree":
        node_count = result.get("node_count")
        ui_tree = result.get("ui_tree")
        tree_type = None
        if isinstance(ui_tree, dict):
            tree_type = ui_tree.get("type")
        return {
            "window_id": result.get("window_id"),
            "node_count": node_count,
            "tree_type": tree_type,
            "ui_tree_omitted": True,
        }

    if tool == "logs_query":
        return {
            "source": result.get("source"),
            "total_lines": result.get("total_lines"),
            "truncated": result.get("truncated"),
            "analysis_type": result.get("analysis_type"),
            "analysis": result.get("analysis"),
        }

    return result


def _result_status(tool: str | None, result: Any) -> str:
    if not isinstance(result, dict):
        return "ok"
    if tool == "find_element":
        if (result.get("count") or 0) == 0:
            return "empty"
    return "ok"


def _safe_structured_content(raw: dict) -> dict:
    sc = raw.get("structuredContent") if isinstance(raw, dict) else None
    if isinstance(sc, dict):
        return sc
    return {
        "tool": "unknown",
        "ok": False,
        "result": None,
        "error": {
            "code": "INVALID_MCP_RESULT",
            "detail": str(raw),
        },
        "meta": {"request_id": None, "duration_ms": None, "timestamp": _now_utc()},
    }


def _to_record(sc: dict, args: dict[str, Any] | None = None, debug: bool = False) -> dict[str, Any]:
    tool = sc.get("tool")
    sanitized = _sanitize_result(tool, sc.get("result"))
    record: dict[str, Any] = {
        "tool": tool,
        "ok": sc.get("ok"),
        "result_status": _result_status(tool, sanitized),
        "result": sanitized,
        "error": sc.get("error"),
        "meta": {
            "request_id": (sc.get("meta") or {}).get("request_id"),
            "duration_ms": (sc.get("meta") or {}).get("duration_ms"),
            "timestamp": _to_utc_z((sc.get("meta") or {}).get("timestamp")),
        },
    }
    if debug:
        record["args"] = args or {}
    return record


async def _call(
    out: list[dict[str, Any]],
    fn: ToolFn,
    args: dict[str, Any],
    debug: bool = False,
    alias: str | None = None,
) -> dict[str, Any]:
    try:
        raw = await fn(**args)
        sc = _safe_structured_content(raw)
        if alias:
            sc["tool"] = alias
        record = _to_record(sc, args=args, debug=debug)
    except Exception as exc:  # pragma: no cover - defensive
        record = {
            "tool": alias or fn.__name__,
            "ok": False,
            "result": None,
            "error": {
                "code": "PY_EXCEPTION",
                "detail": str(exc),
            },
            "meta": {"request_id": None, "duration_ms": None, "timestamp": _now_utc()},
        }
        if debug:
            record["args"] = args
    out.append(record)
    return record


async def run(args: argparse.Namespace) -> dict[str, Any]:
    run_id = f"hmcp-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = output_dir / f"{run_id}-screenshot.jpeg"

    results: list[dict[str, Any]] = []

    # 1) list_devices
    r_list = await _call(results, list_devices, {}, debug=args.debug)
    device_id = None
    devices = (r_list.get("result") or {}).get("devices") or []
    if devices:
        first = devices[0]
        device_id = first.get("device_id") if isinstance(first, dict) else first

    # 2) build_app
    r_build = await _call(
        results,
        build_app,
        {"project_path": args.project_path, "build_mode": "debug"},
        debug=args.debug,
    )
    hap_path = (r_build.get("result") or {}).get("hap_path")

    # 3) install_app
    installed = False
    if hap_path:
        r_install = await _call(
            results,
            install_app,
            {"hap_path": hap_path, "device_id": device_id},
            debug=args.debug,
        )
        installed = bool(r_install.get("ok"))
    else:
        skip = {
            "tool": "install_app",
            "ok": False,
            "result": None,
            "error": {
                "code": "SKIPPED_NO_HAP",
                "detail": "build_app did not return hap_path",
            },
            "meta": {"request_id": None, "duration_ms": None, "timestamp": _now_utc()},
        }
        if args.debug:
            skip["args"] = {"hap_path": None, "device_id": device_id}
        results.append(skip)

    # 4) query_package
    await _call(
        results,
        query_package,
        {"device_id": device_id, "bundle_name": args.bundle_name, "info_type": "abilities"},
        debug=args.debug,
    )

    # 5) run_app
    await _call(
        results,
        run_app,
        {"device_id": device_id, "bundle_name": args.bundle_name},
        debug=args.debug,
    )

    # 6) list_windows
    r_windows = await _call(results, list_windows, {"device_id": device_id}, debug=args.debug)
    windows = (r_windows.get("result") or {}).get("windows") or []
    window_id = None
    if windows and isinstance(windows[0], dict):
        window_id = windows[0].get("window_id")

    # 7) get_ui_tree
    ui_tree_args = {"device_id": device_id}
    if window_id is not None:
        ui_tree_args["window_id"] = window_id
    await _call(results, get_ui_tree, ui_tree_args, debug=args.debug)

    # 8..15) ui tools
    await _call(
        results,
        screenshot,
        {"device_id": device_id, "local_path": str(screenshot_path)},
        debug=args.debug,
    )
    await _call(results, find_element, {"device_id": device_id, "text": "璁剧疆"}, debug=args.debug)
    await _call(results, click_element, {"device_id": device_id, "x": 100, "y": 200}, debug=args.debug)
    await _call(results, long_press_element, {"device_id": device_id, "x": 100, "y": 200}, debug=args.debug)
    await _call(results, swipe, {"device_id": device_id, "direction": "up"}, debug=args.debug)
    await _call(
        results,
        input_text,
        {"device_id": device_id, "x": 120, "y": 220, "text": "mcp_test"},
        debug=args.debug,
    )
    await _call(results, press_key, {"device_id": device_id, "key": "Back"}, debug=args.debug)
    await _call(
        results,
        drag,
        {"device_id": device_id, "from_x": 300, "from_y": 800, "to_x": 300, "to_y": 400},
        debug=args.debug,
    )

    # 16) logs_query
    await _call(
        results,
        logs_query,
        {"device_id": device_id, "lines": 20, "analysis_type": "summary"},
        debug=args.debug,
    )

    # 17) uninstall_app
    if installed:
        await _call(
            results,
            uninstall_app,
            {"device_id": device_id, "bundle_name": args.bundle_name},
            debug=args.debug,
        )
    else:
        skip = {
            "tool": "uninstall_app",
            "ok": False,
            "result": None,
            "error": {
                "code": "SKIPPED_NOT_INSTALLED",
                "detail": "install_app was not successful",
            },
            "meta": {"request_id": None, "duration_ms": None, "timestamp": _now_utc()},
        }
        if args.debug:
            skip["args"] = {"device_id": device_id, "bundle_name": args.bundle_name}
        results.append(skip)

    report = {
        "schema_version": "2.0",
        "run_id": run_id,
        "timestamp": _now_utc(),
        "context": {
            "device_id": device_id,
            "bundle_name": args.bundle_name,
        },
        "summary": {
            "total": len(results),
            "ok": sum(1 for item in results if item.get("ok") is True),
            "failed": sum(1 for item in results if item.get("ok") is False),
        },
        "results": results,
    }
    report_path = output_dir / f"{run_id}-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"REPORT={report_path}")
    print(f"SCREENSHOT={screenshot_path}")
    print(
        f"TOTAL={report['summary']['total']} OK={report['summary']['ok']} FAILED={report['summary']['failed']}"
    )
    return report


def main() -> None:
    args = parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()

