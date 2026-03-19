"""Time parsing helpers for log queries."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Dict, Optional

from ...config import LogSecurityConfig


def _parse_time_expr(expr: str) -> Optional[Dict[str, datetime]]:
    """Parse a small set of natural-language time expressions."""
    if not expr or not expr.strip():
        return None

    expr = expr.strip()
    now = datetime.now()

    match = re.match(r"最近\s*(\d+)\s*(秒|分钟|小时|天)", expr)
    if match:
        count = int(match.group(1))
        unit = match.group(2)
        delta_map = {
            "秒": timedelta(seconds=count),
            "分钟": timedelta(minutes=count),
            "小时": timedelta(hours=count),
            "天": timedelta(days=count),
        }
        delta = delta_map.get(unit)
        if delta:
            return {"start": now - delta, "end": now}

    base_date = None
    remaining = expr

    match = re.match(r"(\d+)\s*天前", remaining)
    if match:
        count = int(match.group(1))
        base_date = (now - timedelta(days=count)).replace(hour=0, minute=0, second=0, microsecond=0)
        remaining = remaining[match.end() :].strip()
    elif remaining.startswith("前天"):
        base_date = (now - timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
        remaining = remaining[2:].strip()
    elif remaining.startswith("昨天"):
        base_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        remaining = remaining[2:].strip()
    elif remaining.startswith("今天"):
        base_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        remaining = remaining[2:].strip()

    period_ranges = {
        "凌晨": (0, 6),
        "上午": (6, 12),
        "中午": (11, 13),
        "下午": (12, 18),
        "晚上": (18, 24),
    }
    period_start = period_end = None
    for period_name, (start_hour, end_hour) in period_ranges.items():
        if period_name in remaining:
            period_start, period_end = start_hour, end_hour
            remaining = remaining.replace(period_name, "").strip()
            break

    if base_date is None and period_start is None:
        return None

    if base_date is None:
        base_date = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if period_start is not None:
        start = base_date.replace(hour=period_start)
        end_hour = min(period_end, 23)
        end = base_date.replace(hour=end_hour, minute=59, second=59)
    else:
        start = base_date
        end = base_date.replace(hour=23, minute=59, second=59)

    if end > now:
        end = now

    return {"start": start, "end": end}


def _expand_short_time(value: str) -> str:
    """Expand HH:MM:SS into a full local datetime string."""
    if len(value) > 8:
        return value

    today = datetime.now()
    candidate = f"{today.strftime('%Y-%m-%d')} {value}"
    try:
        dt = datetime.fromisoformat(candidate)
        if dt > today + timedelta(hours=1):
            if LogSecurityConfig.TIME_PARSE_STRATEGY == "strict":
                raise ValueError(
                    f"time '{value}' is in the future; use a full timestamp (YYYY-MM-DD HH:MM:SS) "
                    "or switch LOG_TIME_PARSE_STRATEGY=auto"
                )
            yesterday = today - timedelta(days=1)
            candidate = f"{yesterday.strftime('%Y-%m-%d')} {value}"
    except ValueError:
        pass
    return candidate


def _needs_historical_logs(start_time: Optional[str], seconds: Optional[int]) -> bool:
    """Return True when the requested window is outside the realtime buffer."""
    if seconds and seconds > 600:
        return True
    if start_time:
        expanded = _expand_short_time(start_time)
        try:
            start_dt = datetime.fromisoformat(expanded)
            return start_dt < datetime.now() - timedelta(minutes=10)
        except ValueError:
            pass
    return False


def _build_time_range(seconds: Optional[int], start_time: Optional[str], end_time: Optional[str]):
    """Build time range filters from the query parameters."""
    now = datetime.now()
    if seconds:
        return {"start": now - timedelta(seconds=seconds), "end": now}

    if start_time or end_time:
        result: dict = {}
        if start_time:
            expanded = _expand_short_time(start_time)
            try:
                result["start"] = datetime.fromisoformat(expanded)
            except ValueError:
                pass
        if end_time:
            expanded = _expand_short_time(end_time)
            try:
                result["end"] = datetime.fromisoformat(expanded)
            except ValueError:
                pass
        return result if result else None

    return None


def _format_file_size(size: int) -> str:
    """Format a file size using KB or MB units."""
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / 1024 / 1024:.1f} MB"
