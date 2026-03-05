"""Unified log query tool."""

import asyncio
import os
from datetime import datetime
from typing import List, Optional

from loguru import logger

from common.tools.registry import mcp_tool

from ...config import LogSecurityConfig
from ...container import get_hdc
from ...types import LogsQueryResult
from ..device_base import ToolBase
from ..response import error_result, from_action_result, mcp_response, ok_result
from .crash_parser import CrashParser
from .historian import _check_and_cleanup_cache, fetch_historical_logs
from .parser import LogParser
from .time_utils import _build_time_range, _format_file_size, _needs_historical_logs, _parse_time_expr

CRASH_LOG_DIR = "/data/log/faultlog/faultlogger"


def _save_logs(output_path, device_id, entries, filters, analysis_result) -> dict:
    if not output_path:
        output_path = f"./hm_logs/hilog_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    valid, result_path = LogSecurityConfig.validate_save_path(output_path)
    if not valid:
        return error_result("PATH_NOT_ALLOWED", str(result_path), result={})

    output_dir = os.path.dirname(result_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(result_path, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("HarmonyOS Log Snapshot\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Device ID: {device_id or 'N/A'}\n")
        f.write(f"Log Lines: {len(entries)}\n")
        active = {k: v for k, v in filters.items() if v}
        if active:
            f.write(f"Filters: {active}\n")
        f.write("=" * 80 + "\n\n")

        if analysis_result and isinstance(analysis_result, dict):
            f.write("--- Analysis Summary ---\n")
            ls = analysis_result.get("level_stats", {})
            if ls:
                f.write(f"Level Stats: {ls}\n")
            tr = analysis_result.get("time_range")
            if tr:
                f.write(f"Time Range: {tr.get('start', 'N/A')} ~ {tr.get('end', 'N/A')}\n")
            f.write("\n")

        f.write("--- Logs ---\n\n")
        for entry in entries:
            f.write(entry.raw_line + "\n")

    file_size = os.path.getsize(result_path)
    return ok_result(
        {
            "saved_path": result_path,
            "file_size": file_size,
            "file_size_human": _format_file_size(file_size),
        }
    )


def _clean_dict(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None}


def _with_device_error_defaults(raw: dict, filters: dict) -> dict:
    base = {"logs": [], "total_lines": 0, "truncated": False, "filters_applied": filters}
    normalized = from_action_result(
        raw,
        default_code="DEVICE_NOT_FOUND",
        default_detail="no device found",
        default_result={},
    )
    if normalized.get("result") is None:
        normalized["result"] = {}
    if isinstance(normalized.get("result"), dict):
        normalized["result"].update(base)
    return normalized


def _fetch_crash_info(hdc, device_id: str, package_name: Optional[str], start_time, end_time) -> Optional[dict]:
    if not package_name:
        return None
    try:
        result = hdc.execute_shell(device_id, f"ls {CRASH_LOG_DIR}")
        if not result.get("success", False):
            return None

        files = result.get("stdout", "").strip().split("\n")
        matched = CrashParser.match_crash_files(files, package_name, start_time, end_time)
        if not matched:
            return None

        latest = matched[0]
        remote_path = f"{CRASH_LOG_DIR}/{latest['filename']}"
        local_dir = os.path.join(os.path.expanduser("~"), "harmonyos-crash")
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, latest["filename"])

        pull_ok = hdc.pull_file(device_id, remote_path, local_path)
        if not pull_ok:
            return {"type": latest["type"], "file": latest["filename"], "error": "pull failed"}

        with open(local_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        crash_info = CrashParser.parse(content, latest["filename"])
        if crash_info:
            return CrashParser.to_dict(crash_info)
        return {"type": latest["type"], "file": latest["filename"]}
    except Exception as e:
        logger.error(f"fetch crash logs failed: {e}")
        return None


def _query_impl(
    device_id=None,
    logs=None,
    input_file=None,
    input_files=None,
    lines=100,
    level=None,
    tag=None,
    tag_search=None,
    keyword=None,
    domain=None,
    pid=None,
    package_name=None,
    start_time=None,
    end_time=None,
    seconds=None,
    analysis_type="summary",
    custom_regex=None,
    save_path=None,
    time_expr=None,
    include_diagnostics=False,
    include_crash=False,
):
    _check_and_cleanup_cache()

    if time_expr and not start_time and not end_time and not seconds:
        parsed = _parse_time_expr(time_expr)
        if parsed:
            start_time = parsed["start"].strftime("%Y-%m-%d %H:%M:%S")
            end_time = parsed["end"].strftime("%Y-%m-%d %H:%M:%S")

    filters = _clean_dict(
        {
            "level": level,
            "tag": tag,
            "tag_search": tag_search,
            "keyword": keyword,
            "domain": domain,
            "pid": pid,
            "package_name": package_name,
            "seconds": seconds,
            "start_time": start_time,
            "end_time": end_time,
        }
    )

    try:
        raw_lines: Optional[List[str]] = None
        _device_id = device_id
        source = "direct"
        extra: dict = {}
        hdc = None

        if logs:
            raw_lines = logs
        elif input_file or input_files:
            paths = list(input_files or [])
            if input_file and input_file not in paths:
                paths.append(input_file)

            all_lines: List[str] = []
            max_file_size = 200 * 1024 * 1024
            for fpath in paths:
                if not os.path.isfile(fpath):
                    return error_result(
                        "FILE_NOT_FOUND",
                        f"file not found: {fpath}",
                        result={"logs": [], "total_lines": 0, "truncated": False, "filters_applied": filters},
                    )
                file_size = os.path.getsize(fpath)
                if file_size > max_file_size:
                    return error_result(
                        "FILE_TOO_LARGE",
                        f"file too large: {fpath} ({_format_file_size(file_size)}), max=200MB",
                        result={"logs": [], "total_lines": 0, "truncated": False, "filters_applied": filters},
                    )
                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        all_lines.extend(f.read().splitlines())
                except OSError as e:
                    return error_result(
                        "FILE_READ_ERROR",
                        f"read file failed: {fpath}: {e}",
                        result={"logs": [], "total_lines": 0, "truncated": False, "filters_applied": filters},
                    )

            raw_lines = all_lines
            source = "file"
        else:
            hdc = get_hdc()
            ok, device = ToolBase.get_device_id(_device_id)
            if not ok:
                return _with_device_error_defaults(device, filters)
            _device_id = device

            if _needs_historical_logs(start_time, seconds):
                source = "persist_file"
                hist = fetch_historical_logs(device, start_time, end_time, lines)
                if not hist.get("success", False):
                    return error_result(
                        hist.get("error_code", "HISTORICAL_LOGS_ERROR"),
                        hist.get("error", "failed to fetch historical logs"),
                        result={
                            "logs": [],
                            "total_lines": 0,
                            "truncated": False,
                            "filters_applied": filters,
                            "dict_used": hist.get("dict_used", False),
                            "dict_status": hist.get("dict_status", "unavailable"),
                            "files_count": hist.get("files_count", 0),
                        },
                    )
                raw_lines = hist.get("raw_lines", [])
                extra["dict_used"] = hist.get("dict_used", False)
                extra["dict_status"] = hist.get("dict_status", "unavailable")
                extra["files_count"] = hist.get("files_count", 0)
            else:
                source = "realtime_buffer"
                resolved_pid = pid
                if package_name and not pid:
                    app_pid = hdc.get_app_pid(device, package_name)
                    if app_pid:
                        resolved_pid = app_pid
                    else:
                        return error_result(
                            "APP_NOT_RUNNING",
                            f"app not running or pid not found: {package_name}",
                            result={
                                "device_id": device,
                                "logs": [],
                                "total_lines": 0,
                                "truncated": False,
                                "filters_applied": filters,
                            },
                        )
                fetch_n = min(lines * LogSecurityConfig.FETCH_MULTIPLIER, LogSecurityConfig.MAX_LOG_LINES)
                log_text = hdc.get_realtime_logs(device, lines=fetch_n, tag=tag, pid=resolved_pid)
                raw_lines = log_text.split("\n") if log_text else []

        entries = LogParser.parse_logs(raw_lines or [])
        time_range = _build_time_range(seconds, start_time, end_time)
        pkg_filter = package_name if (package_name and source != "realtime_buffer") else None

        filter_result = LogParser.filter_entries(
            entries,
            level=level,
            tag=tag,
            tag_search=tag_search,
            keyword=keyword,
            domain=domain,
            time_range=time_range,
            pid=pid,
            seconds=seconds,
            package_name=pkg_filter,
            collect_stats=include_diagnostics,
        )

        if include_diagnostics and isinstance(filter_result, tuple):
            filtered, stats = filter_result
        else:
            filtered = filter_result
            stats = None

        max_n = min(lines, LogSecurityConfig.MAX_LOG_LINES)
        truncated = len(filtered) > max_n
        filtered = filtered[:max_n]

        analysis_result = LogParser.analyze(filtered, analysis_type, custom_regex)
        saved = _save_logs(save_path, _device_id, filtered, filters, analysis_result) if save_path is not None else None

        payload: dict = {
            "device_id": _device_id or "",
            "source": source,
            "logs": [e.raw_line for e in filtered],
            "total_lines": len(filtered),
            "truncated": truncated,
            "filters_applied": _clean_dict(filters),
            "analysis_type": analysis_type,
            "analysis": analysis_result,
            "total_entries_analyzed": len(filtered),
        }
        payload.update(extra)

        if include_diagnostics and stats:
            payload["diagnostics"] = {
                "total_scanned": stats.total_scanned,
                "parse_success": sum(1 for e in entries if e.level),
                "parse_failed": sum(1 for e in entries if not e.level),
                "filter_stats": {
                    "level_filtered": stats.level_filtered,
                    "tag_filtered": stats.tag_filtered,
                    "tag_search_filtered": stats.tag_search_filtered,
                    "keyword_filtered": stats.keyword_filtered,
                    "domain_filtered": stats.domain_filtered,
                    "pid_filtered": stats.pid_filtered,
                    "time_filtered": stats.time_filtered,
                    "package_filtered": stats.package_filtered,
                    "noise_filtered": stats.noise_filtered,
                    "passed": stats.passed,
                },
            }

        if saved:
            if saved.get("ok"):
                payload.update(saved.get("result", {}))
            else:
                return error_result(
                    saved.get("error", {}).get("code", "SAVE_LOGS_ERROR"),
                    saved.get("error", {}).get("detail", "save logs failed"),
                    result=payload,
                )

        if include_crash and hdc and _device_id and package_name:
            start_dt = time_range.get("start") if time_range else None
            end_dt = time_range.get("end") if time_range else None
            crash_info = _fetch_crash_info(hdc, _device_id, package_name, start_dt, end_dt)
            if crash_info:
                payload["crash_info"] = crash_info

        return ok_result(payload)

    except Exception as e:
        return error_result(
            "LOG_QUERY_ERROR",
            str(e),
            result={"logs": [], "total_lines": 0, "truncated": False, "filters_applied": filters},
        )


@mcp_tool(category="general")
@mcp_response("logs_query")
async def logs_query(
    device_id: Optional[str] = None,
    logs: Optional[List[str]] = None,
    input_file: Optional[str] = None,
    input_files: Optional[List[str]] = None,
    lines: int = 100,
    level: Optional[str] = None,
    tag: Optional[str] = None,
    tag_search: Optional[str] = None,
    keyword: Optional[str] = None,
    domain: Optional[str] = None,
    pid: Optional[int] = None,
    package_name: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    seconds: Optional[int] = None,
    analysis_type: str = "summary",
    custom_regex: Optional[str] = None,
    save_path: Optional[str] = None,
    time_expr: Optional[str] = None,
    include_diagnostics: bool = False,
    include_crash: bool = False,
) -> LogsQueryResult:
    return await asyncio.to_thread(
        _query_impl,
        device_id=device_id,
        logs=logs,
        input_file=input_file,
        input_files=input_files,
        lines=lines,
        level=level,
        tag=tag,
        tag_search=tag_search,
        keyword=keyword,
        domain=domain,
        pid=pid,
        package_name=package_name,
        start_time=start_time,
        end_time=end_time,
        seconds=seconds,
        analysis_type=analysis_type,
        custom_regex=custom_regex,
        save_path=save_path,
        time_expr=time_expr,
        include_diagnostics=include_diagnostics,
        include_crash=include_crash,
    )

