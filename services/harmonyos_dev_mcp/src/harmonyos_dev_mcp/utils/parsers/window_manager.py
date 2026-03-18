"""WindowManagerService output parser."""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, Optional

from loguru import logger


WINDOW_LINE_PATTERN = re.compile(
    r"^(\S+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(-?\d+)\s+(\d+)\s+\[\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*\]"
)


def parse_window_list_output(
    stdout: str,
    *,
    resolve_bundle_name: Callable[[int], Optional[str]],
) -> Dict[str, Any]:
    lines = stdout.split("\n")
    header_idx = -1
    for idx, line in enumerate(lines):
        if "WindowName" in line and "WinId" in line:
            header_idx = idx
            break

    pid_bundle_cache: Dict[int, Optional[str]] = {}
    windows = []
    candidate_lines = lines[header_idx + 1 :] if header_idx != -1 else lines
    for raw_line in candidate_lines:
        line = raw_line.strip()
        if not line or line.startswith("-"):
            continue

        match = WINDOW_LINE_PATTERN.match(line)
        if not match:
            continue

        try:
            pid = int(match.group(3))
            zord = int(match.group(8))
            if pid not in pid_bundle_cache:
                pid_bundle_cache[pid] = resolve_bundle_name(pid)
            windows.append(
                {
                    "window_name": match.group(1),
                    "display_id": int(match.group(2)),
                    "pid": pid,
                    "window_id": int(match.group(4)),
                    "type": int(match.group(5)),
                    "mode": int(match.group(6)),
                    "flag": int(match.group(7)),
                    "zord": zord,
                    "bundle_name": pid_bundle_cache.get(pid) or "",
                    "orient": int(match.group(9)),
                    "rect": {
                        "x": int(match.group(10)),
                        "y": int(match.group(11)),
                        "w": int(match.group(12)),
                        "h": int(match.group(13)),
                    },
                    "is_visible": zord > 0,
                }
            )
        except (ValueError, IndexError) as exc:
            logger.debug(f"Failed to parse window line: {line}, error: {exc}")

    if header_idx == -1 and windows:
        logger.warning("Window list header not found, using regex-only parse fallback")

    if stdout.strip() and not windows:
        return {
            "success": False,
            "error_code": "LIST_WINDOWS_PARSE_ERROR",
            "error": "failed to parse any windows from output",
            "windows": [],
            "raw_output": stdout,
        }

    return {
        "success": True,
        "windows": windows,
        "count": len(windows),
    }
