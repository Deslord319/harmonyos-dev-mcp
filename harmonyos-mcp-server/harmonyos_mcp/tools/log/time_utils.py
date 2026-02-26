"""
时间工具模块

提供时间解析、格式化、时间范围构建等功能
"""
import re
from datetime import datetime, timedelta
from typing import Optional, Dict

from ...config import LogSecurityConfig


def _clean_dict(d: dict) -> dict:
    """移除字典中值为 None 的键"""
    return {k: v for k, v in d.items() if v is not None}


def _parse_time_expr(expr: str) -> Optional[Dict[str, datetime]]:
    """解析自然语言时间表达式"""
    if not expr or not expr.strip():
        return None

    expr = expr.strip()
    now = datetime.now()

    m = re.match(r'最近\s*(\d+)\s*(分钟|小时|秒|天)', expr)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        delta_map = {'秒': timedelta(seconds=n), '分钟': timedelta(minutes=n),
                     '小时': timedelta(hours=n), '天': timedelta(days=n)}
        delta = delta_map.get(unit)
        if delta:
            return {'start': now - delta, 'end': now}

    base_date = None
    remaining = expr

    m = re.match(r'(\d+)\s*天前', remaining)
    if m:
        n = int(m.group(1))
        base_date = (now - timedelta(days=n)).replace(hour=0, minute=0, second=0, microsecond=0)
        remaining = remaining[m.end():].strip()
    elif remaining.startswith('前天'):
        base_date = (now - timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
        remaining = remaining[2:].strip()
    elif remaining.startswith('昨天'):
        base_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        remaining = remaining[2:].strip()
    elif remaining.startswith('今天'):
        base_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        remaining = remaining[2:].strip()

    period_ranges = {
        '凌晨': (0, 6),
        '上午': (6, 12),
        '中午': (11, 13),
        '下午': (12, 18),
        '晚上': (18, 24),
    }
    period_start = period_end = None
    for period_name, (h_start, h_end) in period_ranges.items():
        if period_name in remaining:
            period_start, period_end = h_start, h_end
            remaining = remaining.replace(period_name, '').strip()
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

    return {'start': start, 'end': end}


def _expand_short_time(t: str) -> str:
    """将 HH:MM:SS 短格式时间扩展为完整的 YYYY-MM-DD HH:MM:SS"""
    if len(t) > 8:
        return t
    today = datetime.now()
    candidate = f"{today.strftime('%Y-%m-%d')} {t}"
    try:
        dt = datetime.fromisoformat(candidate)
        if dt > today + timedelta(hours=1):
            if LogSecurityConfig.TIME_PARSE_STRATEGY == 'strict':
                raise ValueError(
                    f"时间 '{t}' 在未来，请使用完整日期格式 (YYYY-MM-DD HH:MM:SS) "
                    f"或切换到 auto 模式 (LOG_TIME_PARSE_STRATEGY=auto)"
                )
            yesterday = today - timedelta(days=1)
            candidate = f"{yesterday.strftime('%Y-%m-%d')} {t}"
    except ValueError:
        pass
    return candidate


def _needs_historical_logs(start_time: str, seconds: int) -> bool:
    """判断是否需要从历史落盘文件读取日志"""
    if seconds and seconds > 600:
        return True
    if start_time:
        st = _expand_short_time(start_time)
        try:
            start_dt = datetime.fromisoformat(st)
            return start_dt < datetime.now() - timedelta(minutes=10)
        except ValueError:
            pass
    return False


def _build_time_range(seconds, start_time, end_time):
    """构建时间范围过滤条件"""
    now = datetime.now()
    if seconds:
        return {
            'start': now - timedelta(seconds=seconds),
            'end': now,
        }
    if start_time or end_time:
        tr: dict = {}
        if start_time:
            expanded = _expand_short_time(start_time)
            try:
                tr['start'] = datetime.fromisoformat(expanded)
            except ValueError:
                pass
        if end_time:
            expanded = _expand_short_time(end_time)
            try:
                tr['end'] = datetime.fromisoformat(expanded)
            except ValueError:
                pass
        return tr if tr else None
    return None


def _format_file_size(size: int) -> str:
    """格式化文件大小"""
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / 1024 / 1024:.1f} MB"
