"""Historical hilog fetch and cache management helpers."""

from __future__ import annotations

import os
import re
import shutil
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from loguru import logger

from ...config import LogSecurityConfig
from ...container import get_hdc, get_hilogtool


def _pull_dict_files(hdc, device: str, local_dir: str) -> Optional[str]:
    """Pull and extract hilog dictionary archives from the device."""
    list_result = hdc.execute_shell(device, "ls /data/log/hilog/hilog_dict.*.zip 2>/dev/null")
    if not list_result["success"] or not list_result["stdout"].strip():
        logger.info("no hilog dictionary archives found on device")
        return None

    dict_files = [path.strip() for path in list_result["stdout"].split("\n") if path.strip() and "hilog_dict" in path]
    if not dict_files:
        return None

    tmp_dir = "/data/local/tmp/hilog_dict_tmp"
    hdc.execute_shell(device, f"mkdir -p {tmp_dir}")
    pulled_dicts = []
    try:
        for dict_file in dict_files:
            filename = dict_file.split("/")[-1]
            tmp_path = f"{tmp_dir}/{filename}"
            cp_result = hdc.execute_shell(device, f"cp {dict_file} {tmp_path}")
            if not cp_result["success"]:
                logger.warning(f"failed to copy dictionary archive: {dict_file}")
                continue
            local_path = os.path.join(local_dir, filename)
            if hdc.pull_file(device, tmp_path, local_path):
                pulled_dicts.append(local_path)
    finally:
        hdc.execute_shell(device, f"rm -rf {tmp_dir}")

    if not pulled_dicts:
        return None

    dict_extract_dir = os.path.join(local_dir, "dict_extracted")
    os.makedirs(dict_extract_dir, exist_ok=True)
    try:
        with zipfile.ZipFile(pulled_dicts[0], "r") as archive:
            archive.extractall(dict_extract_dir)
        logger.info(f"dictionary archive extracted to {dict_extract_dir}")
        return dict_extract_dir
    except Exception as exc:
        logger.error(f"failed to extract dictionary archive: {exc}")
        return None


def _cleanup_old_cache_dirs() -> dict:
    """Remove expired hilog_files cache directories."""
    base_dir = Path("./hilog_files")
    if not base_dir.exists():
        return {"cleaned": 0, "freed_bytes": 0, "message": "cache directory does not exist"}

    cutoff = datetime.now() - timedelta(days=LogSecurityConfig.AUTO_CLEANUP_DAYS)
    cleaned_count = 0
    freed_bytes = 0

    for subdir in base_dir.iterdir():
        if not subdir.is_dir():
            continue
        try:
            match = re.search(r"fetch_(\d{8}_\d{6})", subdir.name)
            if not match:
                continue
            dir_time = datetime.strptime(match.group(1), "%Y%m%d_%H%M%S")
            if dir_time >= cutoff:
                continue
            dir_size = sum(file_path.stat().st_size for file_path in subdir.rglob("*") if file_path.is_file())
            shutil.rmtree(subdir)
            cleaned_count += 1
            freed_bytes += dir_size
            logger.info(f"deleted expired hilog cache directory: {subdir}")
        except Exception as exc:  # pragma: no cover - cleanup best effort
            logger.warning(f"failed to clean cache directory {subdir}: {exc}")

    return {
        "cleaned": cleaned_count,
        "freed_bytes": freed_bytes,
        "freed_mb": round(freed_bytes / 1024 / 1024, 2),
        "message": f"cleaned {cleaned_count} expired directories and freed {freed_bytes / 1024 / 1024:.2f} MB",
    }


def _check_and_cleanup_cache() -> None:
    """Trim historical hilog cache when it exceeds the configured size."""
    base_dir = Path("./hilog_files")
    if not base_dir.exists():
        return

    total_size = sum(file_path.stat().st_size for file_path in base_dir.rglob("*") if file_path.is_file())
    total_mb = total_size / 1024 / 1024

    if total_mb > LogSecurityConfig.MAX_CACHE_SIZE_MB:
        logger.warning(
            f"hilog cache size {total_mb:.1f}MB exceeds limit {LogSecurityConfig.MAX_CACHE_SIZE_MB}MB, starting cleanup"
        )
        result = _cleanup_old_cache_dirs()
        logger.info(result["message"])


def fetch_historical_logs(device: str, start_time: Optional[str], end_time: Optional[str], max_lines: int) -> dict:
    """Fetch raw lines from persisted hilog files."""
    hdc = get_hdc()
    hilogtool = get_hilogtool()

    if not hilogtool.is_available():
        return {
            "success": False,
            "error": "hilogtool is unavailable; persisted log parsing cannot continue",
            "hint": "set HILOGTOOL_PATH to hilogtool.exe",
            "error_code": "HILOGTOOL_NOT_AVAILABLE",
            "logs": [],
            "total_lines": 0,
            "truncated": False,
        }

    list_result = hdc.list_hilog_files(device)
    if not list_result["success"] or not list_result.get("files"):
        return {
            "success": False,
            "device_id": device,
            "error": "no historical hilog files found",
            "error_code": "NO_HISTORICAL_FILES",
            "logs": [],
            "total_lines": 0,
            "truncated": False,
        }

    start_dt = end_dt = None
    if start_time:
        from .time_utils import _expand_short_time

        try:
            start_dt = datetime.fromisoformat(_expand_short_time(start_time))
        except ValueError:
            pass
    if end_time:
        from .time_utils import _expand_short_time

        try:
            end_dt = datetime.fromisoformat(_expand_short_time(end_time))
        except ValueError:
            pass

    local_dir = os.path.abspath(f"./hilog_files/fetch_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    os.makedirs(local_dir, exist_ok=True)

    all_files = [
        item for item in list_result["files"] if not item["name"].startswith(("hilog_diag.", "hilog_dict.", "hilog_kmsg."))
    ]

    if start_dt or end_dt:
        buffer = timedelta(hours=1)
        matched = []
        for item in all_files:
            file_ts = item.get("timestamp_dt")
            if not file_ts:
                matched.append(item)
                continue
            if start_dt and file_ts < (start_dt - buffer):
                continue
            if end_dt and file_ts > (end_dt + buffer):
                continue
            matched.append(item)

        matched.sort(key=lambda item: item["timestamp_dt"] if item.get("timestamp_dt") else datetime.min)
        files_to_pull = matched[:15]
    else:
        files_to_pull = all_files[:5]

    if not files_to_pull:
        return {
            "success": False,
            "device_id": device,
            "error": f"no historical logs matched the requested time range: {start_time} ~ {end_time}",
            "error_code": "NO_MATCHING_FILES",
            "logs": [],
            "total_lines": 0,
            "truncated": False,
        }

    logger.info(f"matched {len(files_to_pull)} historical log files: {[item['name'] for item in files_to_pull]}")

    pull_result = hdc.pull_hilog_files(device, files_to_pull, local_dir)
    if not pull_result["success"] or not pull_result.get("pulled_files"):
        return {
            "success": False,
            "device_id": device,
            "error": f"failed to pull matched historical log files ({len(files_to_pull)} candidates)",
            "error_code": "PULL_FILES_FAILED",
            "logs": [],
            "total_lines": 0,
            "truncated": False,
        }

    dict_path = _pull_dict_files(hdc, device, local_dir)
    all_logs: List[str] = []
    dict_used = False
    dict_status = "unavailable"
    cap = min(max_lines * LogSecurityConfig.FETCH_MULTIPLIER, LogSecurityConfig.MAX_LOG_LINES)

    for file_info in pull_result["pulled_files"]:
        local_path = file_info["local_path"]
        logger.info(f"parsing historical log file: {local_path}")
        parsed = hilogtool.parse_and_read(local_path, dict_path=dict_path, max_lines=cap - len(all_logs))
        if parsed["success"]:
            logs = parsed.get("logs", [])
            for line in logs[:10]:
                if "OpenUuidFile fail" in line or "decrypt fail" in line:
                    dict_status = "decrypt_failed"
                    logger.warning("hilogtool output indicates dictionary decryption failure")
                    break
            all_logs.extend(logs)
            if parsed.get("dict_used"):
                dict_used = True
                dict_status = "success"
        else:
            logger.warning(f"failed to parse historical log file {local_path}: {parsed.get('error')}")
        if len(all_logs) >= cap:
            break

    if not all_logs:
        return {
            "success": False,
            "device_id": device,
            "error": "historical log files parsed successfully but produced no content",
            "error_code": "PARSE_EMPTY",
            "logs": [],
            "total_lines": 0,
            "truncated": False,
            "dict_used": dict_used,
            "dict_status": dict_status,
            "files_count": len(pull_result["pulled_files"]),
        }

    return {
        "success": True,
        "raw_lines": all_logs,
        "dict_used": dict_used,
        "dict_status": dict_status,
        "files_count": len(pull_result["pulled_files"]),
        "device_id": device,
    }
