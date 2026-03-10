"""Unified error-focused log query tool."""

import asyncio
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

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
MAX_INPUT_FILE_SIZE = 200 * 1024 * 1024


class LogQueryError(Exception):
    def __init__(self, code: str, detail: str, result: Optional[dict] = None):
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.result = result or {}


def _coerce_optional_int(name: str, value: Optional[int]) -> Optional[int]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise LogQueryError("INVALID_PARAM", f"{name} must be an integer", {})
    if isinstance(value, int):
        return value
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        raise LogQueryError("INVALID_PARAM", f"{name} must be an integer", {})


def _clean_dict(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None}


def _default_result(filters: dict, *, device_id: str = "") -> dict:
    result = {"findings": [], "filters_applied": filters}
    if device_id:
        result["device_id"] = device_id
    return result


def _resolve_time_window(
    start_time: Optional[str], end_time: Optional[str], seconds: Optional[int], time_expr: Optional[str]
) -> Tuple[Optional[str], Optional[str]]:
    if time_expr and not start_time and not end_time and not seconds:
        parsed = _parse_time_expr(time_expr)
        if parsed:
            return (
                parsed["start"].strftime("%Y-%m-%d %H:%M:%S"),
                parsed["end"].strftime("%Y-%m-%d %H:%M:%S"),
            )
    return start_time, end_time


def _save_logs(output_path: Optional[str], device_id: str, findings: List[dict], filters: dict) -> dict:
    target = output_path or f"./hm_logs/hilog_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    valid, result_path = LogSecurityConfig.validate_save_path(target)
    if not valid:
        raise LogQueryError("PATH_NOT_ALLOWED", str(result_path), {})

    output_dir = os.path.dirname(result_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    try:
        with open(result_path, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write("HarmonyOS Log Snapshot\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Device ID: {device_id or 'N/A'}\n")
            f.write(f"Findings: {len(findings)}\n")
            active = {k: v for k, v in filters.items() if v}
            if active:
                f.write(f"Filters: {active}\n")
            f.write("=" * 80 + "\n\n")
            f.write("--- Error Findings ---\n\n")
            for item in findings:
                f.write(f"[{item.get('type', '')}] ")
                if item.get("timestamp"):
                    f.write(f"{item.get('timestamp')} ")
                if item.get("level"):
                    f.write(f"{item.get('level')} ")
                if item.get("tag"):
                    f.write(f"{item.get('tag')}: ")
                f.write(f"{item.get('message', '')}\n")
                f.write(f"RAW: {item.get('raw_line', '')}\n\n")
    except OSError as e:
        raise LogQueryError("SAVE_LOGS_ERROR", f"save logs failed: {e}", {})

    return {"saved_path": result_path}


def _with_device_error_defaults(raw: dict, filters: dict) -> dict:
    normalized = from_action_result(
        raw,
        default_code="DEVICE_NOT_FOUND",
        default_detail="no device found",
        default_result={},
    )
    if normalized.get("result") is None:
        normalized["result"] = {}
    if isinstance(normalized.get("result"), dict):
        normalized["result"].update(_default_result(filters))
    return normalized


def _load_lines_from_files(paths: List[str], filters: dict) -> List[str]:
    all_lines: List[str] = []
    for fpath in paths:
        if not os.path.isfile(fpath):
            raise LogQueryError("FILE_NOT_FOUND", f"file not found: {fpath}", _default_result(filters))
        file_size = os.path.getsize(fpath)
        if file_size > MAX_INPUT_FILE_SIZE:
            raise LogQueryError(
                "FILE_TOO_LARGE",
                f"file too large: {fpath} ({_format_file_size(file_size)}), max=200MB",
                _default_result(filters),
            )
        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                all_lines.extend(f.read().splitlines())
        except OSError as e:
            raise LogQueryError("FILE_READ_ERROR", f"read file failed: {fpath}: {e}", _default_result(filters))
    return all_lines


def _collect_lines(
    *,
    device_id: Optional[str],
    logs: Optional[List[str]],
    input_file: Optional[str],
    input_files: Optional[List[str]],
    lines: int,
    tag: Optional[str],
    pid: Optional[int],
    package_name: Optional[str],
    start_time: Optional[str],
    end_time: Optional[str],
    seconds: Optional[int],
    filters: dict,
) -> Tuple[List[str], str, str, dict, object]:
    if logs:
        return logs, device_id or "", "direct", {}, None

    if input_file or input_files:
        paths = list(input_files or [])
        if input_file and input_file not in paths:
            paths.append(input_file)
        return _load_lines_from_files(paths, filters), device_id or "", "file", {}, None

    hdc = get_hdc()
    ok, resolved_device = ToolBase.get_device_id(device_id)
    if not ok:
        raise LogQueryError(
            "DEVICE_NOT_FOUND",
            "no device found",
            _default_result(filters),
        )

    extra: dict = {}
    if _needs_historical_logs(start_time, seconds):
        hist = fetch_historical_logs(resolved_device, start_time, end_time, lines)
        if not hist.get("success", False):
            raise LogQueryError(
                hist.get("error_code", "HISTORICAL_LOGS_ERROR"),
                hist.get("error", "failed to fetch historical logs"),
                {
                    **_default_result(filters),
                    "dict_used": hist.get("dict_used", False),
                    "dict_status": hist.get("dict_status", "unavailable"),
                    "files_count": hist.get("files_count", 0),
                },
            )
        extra["dict_used"] = hist.get("dict_used", False)
        extra["dict_status"] = hist.get("dict_status", "unavailable")
        extra["files_count"] = hist.get("files_count", 0)
        return hist.get("raw_lines", []), resolved_device, "persist_file", extra, hdc

    resolved_pid = pid
    if package_name and not pid:
        app_pid = hdc.get_app_pid(resolved_device, package_name)
        if not app_pid:
            raise LogQueryError(
                "APP_NOT_RUNNING",
                (
                    f"app not running or pid not found: {package_name}. "
                    "package_name realtime filtering requires the target app to be running; "
                    "for offline or historical analysis use input_file/input_files or a time window."
                ),
                _default_result(filters, device_id=resolved_device),
            )
        resolved_pid = app_pid

    fetch_n = min(lines * LogSecurityConfig.FETCH_MULTIPLIER, LogSecurityConfig.MAX_LOG_LINES)
    text = hdc.get_realtime_logs(resolved_device, lines=fetch_n, tag=tag, pid=resolved_pid)
    return (text.split("\n") if text else []), resolved_device, "realtime_buffer", {}, hdc


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
        if not hdc.pull_file(device_id, remote_path, local_path):
            return {"type": latest["type"], "file": latest["filename"], "error": "pull failed"}

        with open(local_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        crash_info = CrashParser.parse(content, latest["filename"])
        return CrashParser.to_dict(crash_info) if crash_info else {"type": latest["type"], "file": latest["filename"]}
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
    save_path=None,
    time_expr=None,
    include_crash=False,
):
    _check_and_cleanup_cache()
    lines = _coerce_optional_int("lines", lines) or 100
    pid = _coerce_optional_int("pid", pid)
    seconds = _coerce_optional_int("seconds", seconds)
    start_time, end_time = _resolve_time_window(start_time, end_time, seconds, time_expr)
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
        raw_lines, resolved_device, source, extra, hdc = _collect_lines(
            device_id=device_id,
            logs=logs,
            input_file=input_file,
            input_files=input_files,
            lines=lines,
            tag=tag,
            pid=pid,
            package_name=package_name,
            start_time=start_time,
            end_time=end_time,
            seconds=seconds,
            filters=filters,
        )
    except LogQueryError as e:
        if e.code == "DEVICE_NOT_FOUND":
            return _with_device_error_defaults({"success": False, "error": e.detail, "error_code": e.code}, filters)
        return error_result(e.code, e.detail, result=e.result or _default_result(filters))

    try:
        entries = LogParser.parse_logs(raw_lines or [])
        time_range = _build_time_range(seconds, start_time, end_time)
        pkg_filter = package_name if (package_name and source != "realtime_buffer") else None
        filtered = LogParser.filter_entries(
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
        )
        max_n = min(lines, LogSecurityConfig.MAX_LOG_LINES)
        findings = LogParser.extract_effective_errors(filtered[:max_n], limit=max_n)

        payload: dict = {
            "device_id": resolved_device or "",
            "source": source,
            "findings": findings,
            "filters_applied": filters,
        }
        payload.update(extra)

        if save_path is not None:
            try:
                payload.update(_save_logs(save_path, resolved_device, findings, filters))
            except LogQueryError as e:
                return error_result(e.code, e.detail, result=payload)

        if include_crash and hdc and resolved_device and package_name:
            start_dt = time_range.get("start") if time_range else None
            end_dt = time_range.get("end") if time_range else None
            crash_info = _fetch_crash_info(hdc, resolved_device, package_name, start_dt, end_dt)
            if crash_info:
                payload["crash_info"] = crash_info

        return ok_result(payload)

    except Exception as e:
        return error_result("LOG_QUERY_ERROR", str(e), result=_default_result(filters, device_id=resolved_device))


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
    save_path: Optional[str] = None,
    time_expr: Optional[str] = None,
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
        save_path=save_path,
        time_expr=time_expr,
        include_crash=include_crash,
    )
