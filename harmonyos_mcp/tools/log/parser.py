"""
日志解析器模块

提供日志条目定义和解析、过滤、分析功能
"""
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from ...config import LogSecurityConfig


@dataclass
class LogEntry:
    """日志条目结构"""
    timestamp: Optional[datetime] = None
    level: Optional[str] = None
    tag: Optional[str] = None
    pid: Optional[int] = None
    tid: Optional[int] = None
    message: str = ""
    raw_line: str = ""


@dataclass
class FilterStats:
    """过滤统计"""
    total_scanned: int = 0
    level_filtered: int = 0
    tag_filtered: int = 0
    tag_search_filtered: int = 0
    keyword_filtered: int = 0
    domain_filtered: int = 0
    pid_filtered: int = 0
    time_filtered: int = 0
    package_filtered: int = 0
    noise_filtered: int = 0
    passed: int = 0


class LogParser:
    """HarmonyOS hilog 日志解析、过滤与分析"""

    PATTERNS = [
        re.compile(
            r'^(?P<date>\d{2}-\d{2})\s+'
            r'(?P<time>\d{2}:\d{2}:\d{2}\.\d{3})\s+'
            r'(?P<pid>\d+)\s+(?P<tid>\d+)\s+'
            r'(?P<level>[DIWEF])\s+'
            r'(?P<tag>[\w\.\-/]+):\s*(?P<message>.*?)$'
        ),
        re.compile(
            r'^(?P<date>\d{4}-\d{2}-\d{2})\s+'
            r'(?P<time>\d{2}:\d{2}:\d{2}\.\d{3})\s+'
            r'(?P<pid>\d+)\s+(?P<tid>\d+)\s+'
            r'(?P<level>[DIWEF])\s+'
            r'(?P<tag>[\w\.\-/]+):\s*(?P<message>.*?)$'
        ),
        re.compile(
            r'^\[(?P<level>[DIWEF])/(?P<tag>[\w\.\-/]+)'
            r'\((?P<pid>\d+):(?P<tid>\d+)\)\]\s*(?P<message>.*?)$'
        ),
        re.compile(
            r'^(?P<level>[DIWEF])/(?P<tag>[\w\.\-/]+)'
            r'\((?P<pid>\d+)\):\s*(?P<message>.*?)$'
        ),
        re.compile(
            r'^\[(?P<timestamp>\d+)\]'
            r'\[(?P<pid>\d+):(?P<tid>\d+)\]'
            r'\[(?P<level>[DIWEF])\]'
            r'\[(?P<tag>[\w\.\-/]+)\]\s*(?P<message>.*?)$'
        ),
    ]

    LEVEL_NAME_MAP = {
        'D': 'D', 'DEBUG': 'D',
        'I': 'I', 'INFO': 'I',
        'W': 'W', 'WARN': 'W', 'WARNING': 'W',
        'E': 'E', 'ERROR': 'E',
        'F': 'F', 'FATAL': 'F',
    }

    PRIO_MAP = {'D': 0, 'I': 1, 'W': 2, 'E': 3, 'F': 4}

    NOISE_PATTERNS = [
        re.compile(r'/sys/power/last_sr'),
        re.compile(r'XCollie.*last_sr'),
        re.compile(r'Failed to read file:\s*/sys/'),
        re.compile(r'\blogd\b.*\bprune\b', re.IGNORECASE),
        re.compile(r'\bhealthd\b', re.IGNORECASE),
        re.compile(r'\bchatty\b.*\bidentical\b', re.IGNORECASE),
        re.compile(r'ServiceManager:\s*Waiting for service'),
        re.compile(r'\bsuspend\b|\bresume\b', re.IGNORECASE),
        re.compile(r'\bWatchdog\b', re.IGNORECASE),
        re.compile(r'\bGC\b.*(?:pause|heap|allocation)', re.IGNORECASE),
        re.compile(r'\bChoreographer\b', re.IGNORECASE),
    ]

    @classmethod
    def normalize_level(cls, level: Optional[str]) -> Optional[str]:
        if not level:
            return None
        return cls.LEVEL_NAME_MAP.get(level.strip().upper())

    @classmethod
    def normalize_domain(cls, domain: str) -> str:
        if not domain:
            return ""
        d = domain.upper().replace('0X', '').replace('X', '')
        if len(d) == 4:
            return f"C{d}"
        elif len(d) == 5 and d.startswith('C'):
            return d
        elif len(d) == 6:
            return d
        return f"C{d.zfill(4)}"

    @classmethod
    def parse_line(cls, line: str, year: int = None) -> LogEntry:
        if year is None:
            year = datetime.now().year
        line = line.rstrip()
        entry = LogEntry(raw_line=line)

        for pattern in cls.PATTERNS:
            match = pattern.match(line)
            if match:
                groups = match.groupdict()

                if 'date' in groups and 'time' in groups:
                    try:
                        date_str = groups['date']
                        time_str = groups['time']
                        if len(date_str) == 5:
                            date_str = f"{year}-{date_str}"
                        ts = datetime.strptime(
                            f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S.%f"
                        )
                        if ts > datetime.now() + timedelta(days=1):
                            ts = ts.replace(year=ts.year - 1)
                        entry.timestamp = ts
                    except ValueError:
                        pass
                elif 'timestamp' in groups:
                    try:
                        entry.timestamp = datetime.fromtimestamp(
                            int(groups['timestamp']) / 1000.0
                        )
                    except (ValueError, OSError):
                        pass

                entry.level = groups.get('level')
                entry.tag = groups.get('tag')

                if groups.get('pid'):
                    try:
                        entry.pid = int(groups['pid'])
                    except ValueError:
                        pass
                if groups.get('tid'):
                    try:
                        entry.tid = int(groups['tid'])
                    except ValueError:
                        pass

                entry.message = groups.get('message', '').strip()
                break

        if not entry.level:
            entry.message = line
        return entry

    @classmethod
    def parse_logs(cls, lines: List[str], year: int = None) -> List[LogEntry]:
        return [cls.parse_line(line, year) for line in lines if line.strip()]

    @classmethod
    def _is_noise(cls, entry: LogEntry) -> bool:
        text = entry.message or entry.raw_line
        return any(p.search(text) for p in cls.NOISE_PATTERNS)

    @classmethod
    def filter_entries(
        cls,
        entries: List[LogEntry],
        level: Optional[str] = None,
        tag: Optional[str] = None,
        tag_search: Optional[str] = None,
        keyword: Optional[str] = None,
        domain: Optional[str] = None,
        time_range: Optional[Dict] = None,
        pid: Optional[int] = None,
        seconds: Optional[int] = None,
        package_name: Optional[str] = None,
        disable_noise_filter: bool = False,
        collect_stats: bool = False,
    ) -> tuple:
        stats = FilterStats() if collect_stats else None
        min_p = None
        if level:
            normalized = cls.normalize_level(level)
            min_p = cls.PRIO_MAP.get(normalized, 0) if normalized else 0

        tag_lower = tag.lower() if tag else None
        tag_search_lower = tag_search.lower() if tag_search else None
        kw_lower = keyword.lower() if keyword else None
        pkg_lower = package_name.lower() if package_name else None
        domain_norm = cls.normalize_domain(domain) if domain else None

        start_dt = end_dt = None
        if time_range:
            start_dt = time_range.get('start')
            end_dt = time_range.get('end')

        cutoff = None
        if seconds:
            cutoff = datetime.now() - timedelta(seconds=seconds)

        result = []
        for entry in entries:
            if collect_stats:
                stats.total_scanned += 1

            if min_p is not None:
                if not entry.level or cls.PRIO_MAP.get(entry.level.upper(), 0) < min_p:
                    if collect_stats:
                        stats.level_filtered += 1
                    continue

            if tag_lower:
                if not entry.tag or tag_lower not in entry.tag.lower():
                    if collect_stats:
                        stats.tag_filtered += 1
                    continue

            if tag_search_lower:
                if tag_search_lower not in entry.raw_line.lower():
                    if collect_stats:
                        stats.tag_search_filtered += 1
                    continue

            if kw_lower:
                if kw_lower not in entry.raw_line.lower():
                    if collect_stats:
                        stats.keyword_filtered += 1
                    continue

            if domain_norm:
                if domain_norm not in entry.raw_line.upper():
                    if collect_stats:
                        stats.domain_filtered += 1
                    continue

            if pid:
                if entry.pid != pid:
                    if collect_stats:
                        stats.pid_filtered += 1
                    continue

            if start_dt:
                if not entry.timestamp or entry.timestamp < start_dt:
                    if collect_stats:
                        stats.time_filtered += 1
                    continue
            if end_dt:
                if not entry.timestamp or entry.timestamp > end_dt:
                    if collect_stats:
                        stats.time_filtered += 1
                    continue
            if cutoff:
                if not entry.timestamp or entry.timestamp < cutoff:
                    if collect_stats:
                        stats.time_filtered += 1
                    continue

            if pkg_lower:
                if pkg_lower not in entry.raw_line.lower():
                    if collect_stats:
                        stats.package_filtered += 1
                    continue

            if not disable_noise_filter and LogSecurityConfig.ENABLE_NOISE_FILTER:
                if cls._is_noise(entry):
                    if collect_stats:
                        stats.noise_filtered += 1
                    continue

            if collect_stats:
                stats.passed += 1
            result.append(entry)

        if collect_stats:
            return result, stats
        return result

    @classmethod
    def analyze_summary(cls, entries: List[LogEntry]) -> Dict[str, Any]:
        if not entries:
            return {
                'total_lines': 0, 'level_stats': {},
                'top_tags': [], 'top_pids': [], 'time_range': None,
            }

        level_stats = Counter(e.level for e in entries if e.level)
        tag_stats = Counter(e.tag for e in entries if e.tag)
        pid_stats = Counter(e.pid for e in entries if e.pid)

        timestamps = [e.timestamp for e in entries if e.timestamp]
        time_range = None
        if timestamps:
            time_range = {
                'start': min(timestamps).isoformat(),
                'end': max(timestamps).isoformat(),
                'duration_seconds': (max(timestamps) - min(timestamps)).total_seconds(),
            }

        return {
            'total_lines': len(entries),
            'parsed_lines': sum(1 for e in entries if e.level),
            'level_stats': dict(level_stats),
            'top_tags': [
                {'tag': tag, 'count': count}
                for tag, count in tag_stats.most_common(10)
            ],
            'top_pids': [
                {'pid': pid, 'count': count}
                for pid, count in pid_stats.most_common(10)
            ],
            'time_range': time_range,
        }

    @classmethod
    def analyze(
        cls,
        entries: List[LogEntry],
        analysis_type: str = 'summary',
        custom_regex: Optional[str] = None,
    ) -> Dict[str, Any]:
        if analysis_type == 'custom' and custom_regex:
            return cls._analyze_custom(entries, custom_regex)
        return cls.analyze_summary(entries)

    @classmethod
    def _analyze_custom(
        cls, entries: List[LogEntry], regex_pattern: str
    ) -> Dict[str, Any]:
        try:
            pattern = re.compile(regex_pattern)
        except re.error as e:
            return {'success': False, 'error': f'无效的正则表达式: {e}'}

        matches: List[dict] = []
        for entry in entries:
            try:
                m = pattern.search(entry.raw_line)
            except (RecursionError, TimeoutError):
                return {
                    'success': False,
                    'error': '正则表达式执行超时或复杂度过高，请简化表达式',
                }
            if m:
                matches.append({
                    'line': entry.raw_line,
                    'groups': m.groups(),
                    'groupdict': m.groupdict(),
                    'timestamp': entry.timestamp.isoformat() if entry.timestamp else None,
                })

        return {
            'success': True,
            'pattern': regex_pattern,
            'total_matches': len(matches),
            'matches': matches[:100],
        }
