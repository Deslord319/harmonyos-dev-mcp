"""Unified log query tool for error analysis and marker detection."""

from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from loguru import logger

from common.tools.registry import mcp_tool
from common.tools.response import error_result, from_action_result, mcp_response, ok_result

from ...config import LogSecurityConfig
from ...container import get_hdc
from ...types import LogsQueryResult
from ..device_support import DeviceToolSupport
from .crash_parser import CrashParser
from .historian import _check_and_cleanup_cache, fetch_historical_logs
from .parser import LogParser
from .time_utils import _build_time_range, _format_file_size, _needs_historical_logs, _parse_time_expr

CRASH_LOG_DIR = "/data/log/faultlog/faultlogger"
MAX_INPUT_FILE_SIZE = 200 * 1024 * 1024
HM_LOG_DIR = Path("./hm_logs")
ALLOWED_QUERY_MODES = ("errors", "markers")


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


def _coerce_mode(mode: Optional[str]) -> str:
    normalized = (mode or "errors").strip().lower()
    if normalized not in ALLOWED_QUERY_MODES:
        raise LogQueryError(
            "INVALID_QUERY_MODE",
            f'invalid mode. supported values: errors, markers; "{mode}" is not supported',
            {},
        )
    return normalized


def _normalize_keywords(marker_keywords: Optional[Sequence[str]]) -> List[str]:
    if not marker_keywords:
        return []
    result = []
    for keyword in marker_keywords:
        if keyword is None:
            continue
        value = str(keyword).strip()
        if value:
            result.append(value)
    return result


def _resolve_marker_keywords(marker_keywords: Sequence[str]) -> List[str]:
    if marker_keywords:
        return list(marker_keywords)
    return list(LogParser.DEFAULT_MARKER_KEYWORDS)


def _clean_dict(values: dict) -> dict:
    return {key: value for key, value in values.items() if value is not None}


def _default_result(
    filters: dict,
    *,
    query_mode: str,
    device_id: str = "",
    source_attempted: Optional[List[str]] = None,
    source_used: str = "",
) -> dict:
    result = {
        "query_mode": query_mode,
        "source_attempted": source_attempted or [],
        "source_used": source_used,
        "fallback_triggered": False,
        "matched": False,
        "match_count": 0,
        "group_count": 0,
        "items": [],
        "filters_applied": filters,
    }
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


def _save_logs(output_path: Optional[str], device_id: str, items: List[dict], filters: dict, query_mode: str) -> dict:
    target = output_path or f"./hm_logs/hilog_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    valid, result_path = LogSecurityConfig.validate_save_path(target)
    if not valid:
        raise LogQueryError("PATH_NOT_ALLOWED", str(result_path), {})

    output_dir = os.path.dirname(result_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    try:
        with open(result_path, "w", encoding="utf-8") as file_obj:
            file_obj.write("=" * 80 + "\n")
            file_obj.write("HarmonyOS Log Snapshot\n")
            file_obj.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            file_obj.write(f"Device ID: {device_id or 'N/A'}\n")
            file_obj.write(f"Mode: {query_mode}\n")
            file_obj.write(f"Items: {len(items)}\n")
            active = {key: value for key, value in filters.items() if value}
            if active:
                file_obj.write(f"Filters: {active}\n")
            file_obj.write("=" * 80 + "\n\n")
            for item in items:
                file_obj.write(f"[{item.get('type', '')}] ")
                if item.get("timestamp"):
                    file_obj.write(f"{item.get('timestamp')} ")
                if item.get("level"):
                    file_obj.write(f"{item.get('level')} ")
                if item.get("tag"):
                    file_obj.write(f"{item.get('tag')}: ")
                file_obj.write(f"{item.get('message', '')}\n")
                if item.get("matched_keywords"):
                    file_obj.write(f"MATCHED: {item.get('matched_keywords')}\n")
                if item.get("context_before"):
                    file_obj.write(f"CONTEXT BEFORE: {item.get('context_before')}\n")
                file_obj.write(f"RAW: {item.get('raw_line', '')}\n")
                if item.get("context_after"):
                    file_obj.write(f"CONTEXT AFTER: {item.get('context_after')}\n")
                file_obj.write("\n")
    except OSError as exc:
        raise LogQueryError("SAVE_LOGS_ERROR", f"save logs failed: {exc}", {})

    return {"saved_path": result_path}


def _cleanup_old_saved_logs() -> dict:
    """Clean expired files under hm_logs."""
    if not HM_LOG_DIR.exists():
        return {"cleaned": 0, "freed_bytes": 0}

    cutoff = datetime.now() - timedelta(days=LogSecurityConfig.AUTO_CLEANUP_DAYS)
    cleaned_count = 0
    freed_bytes = 0

    for log_file in HM_LOG_DIR.glob("*.txt"):
        try:
            file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if file_mtime < cutoff:
                file_size = log_file.stat().st_size
                log_file.unlink()
                cleaned_count += 1
                freed_bytes += file_size
                logger.info(f"deleted expired saved log snapshot: {log_file}")
        except Exception as exc:  # pragma: no cover - best effort cleanup
            logger.warning(f"failed to clean saved log snapshot {log_file}: {exc}")

    return {"cleaned": cleaned_count, "freed_bytes": freed_bytes}


def _check_and_cleanup_saved_logs() -> None:
    """Keep hm_logs within the configured retention and size limits."""
    if not HM_LOG_DIR.exists():
        return

    _cleanup_old_saved_logs()

    max_dir_size_mb = LogSecurityConfig.MAX_CACHE_SIZE_MB
    files = [path for path in HM_LOG_DIR.glob("*.txt") if path.is_file()]
    total_size = sum(path.stat().st_size for path in files)
    total_mb = total_size / 1024 / 1024

    if total_mb <= max_dir_size_mb:
        return

    for log_file in sorted(files, key=lambda path: path.stat().st_mtime):
        if total_mb <= max_dir_size_mb:
            break
        try:
            file_size = log_file.stat().st_size
            log_file.unlink()
            total_size -= file_size
            total_mb = total_size / 1024 / 1024
            logger.info(f"deleted saved log snapshot due to size limit: {log_file}")
        except Exception as exc:  # pragma: no cover - best effort cleanup
            logger.warning(f"failed to trim saved log snapshot {log_file}: {exc}")


def _with_device_error_defaults(raw: dict, filters: dict, query_mode: str) -> dict:
    normalized = from_action_result(
        raw,
        default_code="DEVICE_NOT_FOUND",
        default_detail="no device found",
        default_result={},
    )
    if normalized.get("result") is None:
        normalized["result"] = {}
    if isinstance(normalized.get("result"), dict):
        normalized["result"].update(_default_result(filters, query_mode=query_mode))
    return normalized


def _load_lines_from_files(paths: List[str], filters: dict, query_mode: str) -> List[str]:
    all_lines: List[str] = []
    for file_path in paths:
        if not os.path.isfile(file_path):
            raise LogQueryError("FILE_NOT_FOUND", f"file not found: {file_path}", _default_result(filters, query_mode=query_mode))
        file_size = os.path.getsize(file_path)
        if file_size > MAX_INPUT_FILE_SIZE:
            raise LogQueryError(
                "FILE_TOO_LARGE",
                f"file too large: {file_path} ({_format_file_size(file_size)}), max=200MB",
                _default_result(filters, query_mode=query_mode),
            )
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as file_obj:
                all_lines.extend(file_obj.read().splitlines())
        except OSError as exc:
            raise LogQueryError(
                "FILE_READ_ERROR",
                f"read file failed: {file_path}: {exc}",
                _default_result(filters, query_mode=query_mode),
            )
    return all_lines


def _collect_realtime_lines(
    *,
    hdc,
    device_id: str,
    lines: int,
    tag: Optional[str],
    pid: Optional[int],
    realtime_wait_ms: int,
) -> List[str]:
    attempts = 1 if realtime_wait_ms <= 0 else 3
    delay_seconds = max(realtime_wait_ms / max(attempts, 1) / 1000.0, 0.0)
    merged: List[str] = []
    seen = set()

    for index in range(attempts):
        text = hdc.get_realtime_logs(device_id, lines=lines, tag=tag, pid=pid)
        for line in (text.splitlines() if text else []):
            normalized = line.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            merged.append(normalized)
        if index < attempts - 1 and delay_seconds > 0:
            time.sleep(delay_seconds)
    return merged


def _get_related_pids(hdc, device_id: str, package_name: Optional[str], explicit_pid: Optional[int]) -> List[int]:
    if explicit_pid:
        return [explicit_pid]
    if not package_name:
        return []
    app_pid = hdc.get_app_pid(device_id, package_name)
    return [app_pid] if app_pid else []


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
    realtime_wait_ms: int,
    fallback_to_historical: bool,
    filters: dict,
    query_mode: str,
) -> Tuple[List[Tuple[str, List[str], dict]], str, object]:
    if logs:
        return [("direct", logs, {})], device_id or "", None

    if input_file or input_files:
        paths = list(input_files or [])
        if input_file and input_file not in paths:
            paths.append(input_file)
        return [("file", _load_lines_from_files(paths, filters, query_mode), {})], device_id or "", None

    hdc = get_hdc()
    ok, resolved_device = DeviceToolSupport.get_device_id(device_id)
    if not ok:
        raise LogQueryError("DEVICE_NOT_FOUND", "no device found", _default_result(filters, query_mode=query_mode))

    fetch_n = min(lines * LogSecurityConfig.FETCH_MULTIPLIER, LogSecurityConfig.MAX_LOG_LINES)
    sources: List[Tuple[str, List[str], dict]] = []
    prefer_historical = bool(start_time or end_time) or _needs_historical_logs(start_time, seconds)

    if prefer_historical:
        hist = fetch_historical_logs(resolved_device, start_time, end_time, lines)
        if not hist.get("success", False):
            raise LogQueryError(
                hist.get("error_code", "HISTORICAL_LOGS_ERROR"),
                hist.get("error", "failed to fetch historical logs"),
                {
                    **_default_result(filters, query_mode=query_mode, device_id=resolved_device),
                    "dict_used": hist.get("dict_used", False),
                    "files_count": hist.get("files_count", 0),
                },
            )
        sources.append(
            (
                "persist_file",
                hist.get("raw_lines", []),
                {
                    "dict_used": hist.get("dict_used", False),
                    "dict_status": hist.get("dict_status", "unavailable"),
                    "files_count": hist.get("files_count", 0),
                },
            )
        )
        return sources, resolved_device, hdc

    realtime_lines = _collect_realtime_lines(
        hdc=hdc,
        device_id=resolved_device,
        lines=fetch_n,
        tag=tag,
        pid=pid,
        realtime_wait_ms=realtime_wait_ms,
    )
    sources.append(("realtime_buffer", realtime_lines, {}))

    if fallback_to_historical:
        hist = fetch_historical_logs(resolved_device, start_time, end_time, lines)
        if hist.get("success", False):
            sources.append(
                (
                    "persist_file",
                    hist.get("raw_lines", []),
                    {
                        "dict_used": hist.get("dict_used", False),
                        "dict_status": hist.get("dict_status", "unavailable"),
                        "files_count": hist.get("files_count", 0),
                    },
                )
            )
    return sources, resolved_device, hdc


def _extract_items(
    *,
    entries,
    query_mode: str,
    lines: int,
    marker_keywords: Optional[Sequence[str]],
    context_lines: int,
    package_name: Optional[str] = None,
    related_pids: Optional[Sequence[int]] = None,
) -> dict:
    max_items = min(lines, LogSecurityConfig.MAX_LOG_LINES)
    if query_mode == "markers":
        marker_result = LogParser.extract_marker_items(
            entries,
            limit=max_items,
            marker_keywords=marker_keywords,
            context_lines=context_lines,
            package_name=package_name,
            related_pids=related_pids,
        )
        return marker_result
    return {
        "items": LogParser.extract_error_items(entries, limit=max_items, context_lines=context_lines),
        "match_count": 0,
        "group_count": 0,
    }


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

        with open(local_path, "r", encoding="utf-8", errors="replace") as file_obj:
            content = file_obj.read()
        crash_info = CrashParser.parse(content, latest["filename"])
        return CrashParser.to_dict(crash_info) if crash_info else {"type": latest["type"], "file": latest["filename"]}
    except Exception as exc:  # pragma: no cover - device side best effort
        logger.error(f"fetch crash logs failed: {exc}")
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
    mode="errors",
    marker_keywords=None,
    fallback_to_historical=False,
    realtime_wait_ms=1000,
    context_lines=0,
):
    _check_and_cleanup_cache()
    _check_and_cleanup_saved_logs()

    try:
        query_mode = _coerce_mode(mode)
        lines = _coerce_optional_int("lines", lines) or 100
        pid = _coerce_optional_int("pid", pid)
        seconds = _coerce_optional_int("seconds", seconds)
        realtime_wait_ms = _coerce_optional_int("realtime_wait_ms", realtime_wait_ms) or 0
        context_lines = _coerce_optional_int("context_lines", context_lines) or 0
        marker_keywords = _normalize_keywords(marker_keywords)
    except LogQueryError as exc:
        return error_result(exc.code, exc.detail, result=exc.result or {})

    active_marker_keywords = _resolve_marker_keywords(marker_keywords)

    start_time, end_time = _resolve_time_window(start_time, end_time, seconds, time_expr)
    filters = _clean_dict(
        {
            "mode": query_mode,
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
            "marker_keywords": active_marker_keywords or None,
        }
    )

    try:
        source_batches, resolved_device, hdc = _collect_lines(
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
            realtime_wait_ms=realtime_wait_ms,
            fallback_to_historical=fallback_to_historical,
            filters=filters,
            query_mode=query_mode,
        )
    except LogQueryError as exc:
        if exc.code == "DEVICE_NOT_FOUND":
            return _with_device_error_defaults({"success": False, "error": exc.detail, "error_code": exc.code}, filters, query_mode)
        return error_result(exc.code, exc.detail, result=exc.result or _default_result(filters, query_mode=query_mode))

    try:
        related_pids = _get_related_pids(hdc, resolved_device, package_name, pid) if hdc else ([pid] if pid else [])
        related_keywords = list(LogParser.DEFAULT_RELATED_KEYWORDS) if query_mode == "markers" else []
        time_range = _build_time_range(seconds, start_time, end_time)

        attempted = [source_name for source_name, _, _ in source_batches]
        payload = _default_result(
            filters,
            query_mode=query_mode,
            device_id=resolved_device,
            source_attempted=attempted,
            source_used=attempted[0] if attempted else "",
        )

        for source_name, raw_lines, extra in source_batches:
            entries = LogParser.parse_logs(raw_lines or [])
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
                package_name=package_name if package_name else None,
                related_pids=related_pids,
                related_keywords=related_keywords,
                allow_related_without_package=query_mode == "markers" and bool(package_name),
            )
            extraction = _extract_items(
                entries=filtered,
                query_mode=query_mode,
                lines=lines,
                marker_keywords=active_marker_keywords,
                context_lines=context_lines,
                package_name=package_name,
                related_pids=related_pids,
            )
            items = extraction["items"]
            payload.update(extra)
            payload["source_used"] = source_name
            payload["items"] = items
            payload["matched"] = bool(items)
            if query_mode == "markers":
                payload["match_count"] = extraction["match_count"]
                payload["group_count"] = extraction["group_count"]
            else:
                payload["match_count"] = len(items)
                payload["group_count"] = len(items)
            payload["fallback_triggered"] = source_name == "persist_file" and len(attempted) > 1
            if items or source_name == attempted[-1]:
                break

        if save_path is not None:
            try:
                payload.update(_save_logs(save_path, resolved_device, payload["items"], filters, query_mode))
            except LogQueryError as exc:
                return error_result(exc.code, exc.detail, result=payload)

        if include_crash and hdc and resolved_device and package_name:
            start_dt = time_range.get("start") if time_range else None
            end_dt = time_range.get("end") if time_range else None
            crash_info = _fetch_crash_info(hdc, resolved_device, package_name, start_dt, end_dt)
            if crash_info:
                payload["crash_info"] = crash_info

        return ok_result(payload)

    except Exception as exc:  # pragma: no cover - safety net
        return error_result(
            "LOG_QUERY_ERROR",
            str(exc),
            result=_default_result(filters, query_mode=query_mode, device_id=resolved_device),
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
    save_path: Optional[str] = None,
    time_expr: Optional[str] = None,
    include_crash: bool = False,
    mode: str = "errors",
    marker_keywords: Optional[List[str]] = None,
    fallback_to_historical: bool = False,
    realtime_wait_ms: int = 1000,
    context_lines: int = 0,
) -> LogsQueryResult:
    """Query HarmonyOS logs for errors or business markers.

    Default mode focuses on actionable errors. Use ``mode="markers"`` to confirm
    success or failure markers such as picker save results.
    """

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
        mode=mode,
        marker_keywords=marker_keywords,
        fallback_to_historical=fallback_to_historical,
        realtime_wait_ms=realtime_wait_ms,
        context_lines=context_lines,
    )
