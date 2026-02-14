"""
日志查询工具

合并原有 hilog_receive / logs_fetch / logs_save_snapshot / logs_analyze
为单一 logs_query 工具，实现 拉取 -> 解析 -> 过滤 -> 分析 -> 保存 一体化流程。
"""
import asyncio
import os
import re
import statistics
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from loguru import logger

from ..container import get_hdc, get_hilogtool
from ..config import LogSecurityConfig
from ..types import LogsQueryResult
from .base import ToolBase
from .registry import mcp_tool


# ============================================================================
# 日志条目
# ============================================================================

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

    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'level': self.level,
            'tag': self.tag,
            'pid': self.pid,
            'tid': self.tid,
            'message': self.message,
            'raw_line': self.raw_line,
        }


# ============================================================================
# 日志解析器
# ============================================================================

class LogParser:
    """HarmonyOS hilog 日志解析、过滤与分析"""

    # --- 正则模式 --------------------------------------------------------

    PATTERNS = [
        # 格式1: 01-31 14:30:25.123  1234  5678 I MyApp: message
        re.compile(
            r'^(?P<date>\d{2}-\d{2})\s+'
            r'(?P<time>\d{2}:\d{2}:\d{2}\.\d{3})\s+'
            r'(?P<pid>\d+)\s+(?P<tid>\d+)\s+'
            r'(?P<level>[DIWEF])\s+'
            r'(?P<tag>[\w\.\-/]+):\s*(?P<message>.*?)$'
        ),
        # 格式2: 2026-01-31 14:30:25.123  1234  5678 I MyApp: message
        re.compile(
            r'^(?P<date>\d{4}-\d{2}-\d{2})\s+'
            r'(?P<time>\d{2}:\d{2}:\d{2}\.\d{3})\s+'
            r'(?P<pid>\d+)\s+(?P<tid>\d+)\s+'
            r'(?P<level>[DIWEF])\s+'
            r'(?P<tag>[\w\.\-/]+):\s*(?P<message>.*?)$'
        ),
        # 格式3: [I/MyApp(1234:5678)] message
        re.compile(
            r'^\[(?P<level>[DIWEF])/(?P<tag>[\w\.\-/]+)'
            r'\((?P<pid>\d+):(?P<tid>\d+)\)\]\s*(?P<message>.*?)$'
        ),
        # 格式4: I/MyApp(1234): message
        re.compile(
            r'^(?P<level>[DIWEF])/(?P<tag>[\w\.\-/]+)'
            r'\((?P<pid>\d+)\):\s*(?P<message>.*?)$'
        ),
        # 格式5: [timestamp][PID:TID][LEVEL][TAG] message
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

    ERROR_PATTERNS = {
        'exception': re.compile(r'(?i)(exception|error|fail|crash)', re.IGNORECASE),
        'anr': re.compile(r'(?i)(anr|application not responding)', re.IGNORECASE),
        'crash': re.compile(r'(?i)(crash|fatal|abort|segfault|sigsegv)', re.IGNORECASE),
        'oom': re.compile(r'(?i)(out\s*of\s*memory|oom|memory\s*allocation\s*failed)', re.IGNORECASE),
        'timeout': re.compile(r'(?i)(timeout|timed?\s*out)', re.IGNORECASE),
    }

    NOISE_PATTERNS = [
        re.compile(r'/sys/power/last_sr'),
        re.compile(r'XCollie.*last_sr'),
        re.compile(r'Failed to read file:\s*/sys/'),
    ]

    KEYWORD_PATTERNS = {
        'error_code': re.compile(
            r'(?:code|error|errno|status|ret|result)\s*[:=]\s*(-?\d+)', re.IGNORECASE),
        'component': re.compile(
            r'\[(\w+)\]\[(\w+)\]|\[([A-Z][a-zA-Z]+)\]|<([A-Z][a-zA-Z]+)>'),
        'exception_name': re.compile(
            r'\b([A-Z][a-zA-Z]*(?:Exception|Error|Failure|Fault))\b'),
        'error_phrase': re.compile(
            r'((?:Failed|Unable|Cannot|Could not|Couldn\'t|Error|Fail)'
            r'\s+to\s+[\w\s]+?)(?:\.|,|$|Cause)', re.IGNORECASE),
        'message_content': re.compile(
            r'(?:msg|message|reason|cause)\s*[:=]\s*([^,\n\.]+)', re.IGNORECASE),
    }

    PERF_PATTERNS = {
        'duration': re.compile(
            r'(?i)(cost|duration|elapsed|time|took|spent)'
            r'\s*[:\s=]*\s*(\d+(?:\.\d+)?)\s*(ms|s|μs|us|ns)?'),
        'latency': re.compile(
            r'(?i)latency\s*[:\s=]*\s*(\d+(?:\.\d+)?)\s*(ms|s)?'),
    }

    # --- 解析 -------------------------------------------------------------

    @classmethod
    def normalize_level(cls, level: Optional[str]) -> Optional[str]:
        """将各种级别写法归一化为单字符 (D/I/W/E/F)"""
        if not level:
            return None
        return cls.LEVEL_NAME_MAP.get(level.strip().upper())

    @classmethod
    def parse_line(cls, line: str, year: int = None) -> LogEntry:
        """解析单行日志"""
        if year is None:
            year = datetime.now().year
        line = line.rstrip()
        entry = LogEntry(raw_line=line)

        for pattern in cls.PATTERNS:
            match = pattern.match(line)
            if match:
                groups = match.groupdict()

                # 解析时间戳
                if 'date' in groups and 'time' in groups:
                    try:
                        date_str = groups['date']
                        time_str = groups['time']
                        if len(date_str) == 5:  # MM-DD
                            date_str = f"{year}-{date_str}"
                        entry.timestamp = datetime.strptime(
                            f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S.%f"
                        )
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
        """批量解析日志"""
        return [cls.parse_line(line, year) for line in lines if line.strip()]

    # --- 过滤 -------------------------------------------------------------

    @classmethod
    def _is_noise(cls, entry: LogEntry) -> bool:
        """检查日志条目是否为系统噪声"""
        text = entry.message or entry.raw_line
        return any(p.search(text) for p in cls.NOISE_PATTERNS)

    @classmethod
    def filter_entries(
        cls,
        entries: List[LogEntry],
        level: Optional[str] = None,
        tag: Optional[str] = None,
        keyword: Optional[str] = None,
        time_range: Optional[Dict] = None,
        pid: Optional[int] = None,
        seconds: Optional[int] = None
    ) -> List[LogEntry]:
        """过滤日志条目"""
        filtered = entries

        if level:
            normalized = cls.normalize_level(level)
            prio = {'D': 0, 'I': 1, 'W': 2, 'E': 3, 'F': 4}
            min_p = prio.get(normalized, 0) if normalized else 0
            filtered = [
                e for e in filtered
                if e.level and prio.get(e.level.upper(), 0) >= min_p
            ]

        if tag:
            filtered = [
                e for e in filtered
                if e.tag and tag.lower() in e.tag.lower()
            ]

        if keyword:
            kw = keyword.lower()
            filtered = [
                e for e in filtered
                if kw in e.message.lower() or kw in e.raw_line.lower()
            ]

        if pid:
            filtered = [e for e in filtered if e.pid == pid]

        if time_range:
            start = time_range.get('start')
            end = time_range.get('end')
            if start:
                try:
                    start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    filtered = [
                        e for e in filtered
                        if e.timestamp and e.timestamp >= start_dt
                    ]
                except ValueError:
                    pass
            if end:
                try:
                    end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                    filtered = [
                        e for e in filtered
                        if e.timestamp and e.timestamp <= end_dt
                    ]
                except ValueError:
                    pass

        if seconds:
            cutoff = datetime.now() - timedelta(seconds=seconds)
            filtered = [
                e for e in filtered
                if e.timestamp and e.timestamp >= cutoff
            ]

        return filtered

    # --- 分析 -------------------------------------------------------------

    @classmethod
    def analyze_summary(cls, entries: List[LogEntry]) -> Dict[str, Any]:
        """生成日志摘要分析"""
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
    def analyze_errors(cls, entries: List[LogEntry]) -> Dict[str, Any]:
        """分析错误日志"""
        errors = [
            e for e in entries
            if e.level in ('E', 'F') and not cls._is_noise(e)
        ]

        by_tag: Dict[str, list] = defaultdict(list)
        for entry in errors:
            tag = entry.tag or 'Unknown'
            by_tag[tag].append({
                'message': entry.message,
                'timestamp': entry.timestamp.isoformat() if entry.timestamp else None,
                'pid': entry.pid,
                'level': entry.level,
            })

        error_types: Dict[str, list] = defaultdict(list)
        for entry in entries:
            if cls._is_noise(entry):
                continue
            for error_type, pattern in cls.ERROR_PATTERNS.items():
                if pattern.search(entry.message) or pattern.search(entry.raw_line):
                    error_types[error_type].append({
                        'message': entry.message[:200],
                        'timestamp': entry.timestamp.isoformat() if entry.timestamp else None,
                        'tag': entry.tag,
                        'level': entry.level,
                    })

        return {
            'total_errors': len(errors),
            'error_level_count': sum(1 for e in errors if e.level == 'E'),
            'fatal_level_count': sum(1 for e in errors if e.level == 'F'),
            'by_tag': {
                tag: {'count': len(items), 'samples': items[:5]}
                for tag, items in by_tag.items()
            },
            'error_types': {
                et: {'count': len(items), 'samples': items[:3]}
                for et, items in error_types.items()
            },
        }

    @classmethod
    def analyze_performance(cls, entries: List[LogEntry]) -> Dict[str, Any]:
        """分析性能相关日志"""
        durations_ms: List[float] = []
        perf_logs: List[dict] = []

        for entry in entries:
            text = entry.message + ' ' + entry.raw_line
            for _, pattern in cls.PERF_PATTERNS.items():
                for match in pattern.findall(text):
                    try:
                        if len(match) >= 2:
                            value = float(match[1]) if isinstance(match, tuple) else float(match)
                            unit = match[2] if len(match) > 2 and match[2] else 'ms'
                        else:
                            continue

                        if unit == 's':
                            value *= 1000
                        elif unit in ('μs', 'us'):
                            value /= 1000
                        elif unit == 'ns':
                            value /= 1000000

                        durations_ms.append(value)
                        perf_logs.append({
                            'message': entry.message[:100],
                            'value_ms': value,
                            'tag': entry.tag,
                            'timestamp': entry.timestamp.isoformat() if entry.timestamp else None,
                        })
                    except (ValueError, TypeError, IndexError):
                        continue

        result: Dict[str, Any] = {
            'total_perf_logs': len(perf_logs),
            'duration_samples': len(durations_ms),
            'samples': perf_logs[:10],
        }

        if durations_ms:
            sorted_d = sorted(durations_ms)
            result['statistics'] = {
                'min_ms': round(min(durations_ms), 2),
                'max_ms': round(max(durations_ms), 2),
                'avg_ms': round(statistics.mean(durations_ms), 2),
                'median_ms': round(statistics.median(durations_ms), 2),
            }
            if len(sorted_d) >= 20:
                result['statistics']['p95_ms'] = round(
                    sorted_d[int(len(sorted_d) * 0.95)], 2
                )
                result['statistics']['p99_ms'] = round(
                    sorted_d[int(len(sorted_d) * 0.99)], 2
                )

        return result

    @classmethod
    def analyze_crashes(cls, entries: List[LogEntry]) -> Dict[str, Any]:
        """分析崩溃相关日志"""
        crashes: List[dict] = []
        anrs: List[dict] = []
        exceptions: List[dict] = []

        for entry in entries:
            text = entry.message + ' ' + entry.raw_line
            if cls.ERROR_PATTERNS['crash'].search(text):
                crashes.append(entry.to_dict())
            if cls.ERROR_PATTERNS['anr'].search(text):
                anrs.append(entry.to_dict())
            if cls.ERROR_PATTERNS['exception'].search(text):
                exceptions.append(entry.to_dict())

        return {
            'crashes': {'count': len(crashes), 'samples': crashes[:5]},
            'anrs': {'count': len(anrs), 'samples': anrs[:5]},
            'exceptions': {'count': len(exceptions), 'samples': exceptions[:10]},
            'next_steps': cls._generate_next_steps(crashes, anrs, exceptions),
        }

    @classmethod
    def _generate_next_steps(cls, crashes: List, anrs: List, exceptions: List) -> List[str]:
        """根据日志证据生成排查建议"""
        steps: List[str] = []
        if crashes:
            steps.append(
                "发现崩溃日志，建议：1) 检查崩溃堆栈信息 "
                "2) 使用 addr2line 解析地址 3) 检查相关内存操作"
            )
        if anrs:
            steps.append(
                "发现 ANR 日志，建议：1) 检查主线程阻塞操作 "
                "2) 分析 trace 文件 3) 检查 Binder 调用超时"
            )
        if exceptions:
            steps.append(
                "发现异常日志，建议：1) 检查异常堆栈 "
                "2) 确认异常触发条件 3) 检查相关输入参数"
            )
        if not steps:
            steps.append("未发现明显的崩溃或异常模式")
        return steps

    @classmethod
    def analyze_keywords(cls, entries: List[LogEntry]) -> Dict[str, Any]:
        """分析日志中的异常并提取可检索关键词"""
        error_entries = [e for e in entries if e.level in ('E', 'F', 'W')]

        if not error_entries:
            return {
                'total_errors': 0,
                'error_groups': [],
                'search_keywords': [],
                'message': '未发现错误或警告日志',
            }

        error_groups: Dict[str, list] = defaultdict(list)
        for entry in error_entries:
            error_groups[entry.tag or 'Unknown'].append(entry)

        analyzed_groups: List[dict] = []
        all_keywords: set = set()
        for tag, group_entries in error_groups.items():
            ga = cls._analyze_error_group(tag, group_entries)
            analyzed_groups.append(ga)
            all_keywords.update(ga.get('keywords', []))

        analyzed_groups.sort(key=lambda x: x['count'], reverse=True)

        return {
            'total_errors': len(error_entries),
            'error_groups': analyzed_groups,
            'search_keywords': cls._rank_keywords(all_keywords, error_entries),
            'summary': {
                'unique_tags': len(error_groups),
                'error_count': sum(1 for e in error_entries if e.level == 'E'),
                'fatal_count': sum(1 for e in error_entries if e.level == 'F'),
                'warning_count': sum(1 for e in error_entries if e.level == 'W'),
            },
        }

    @classmethod
    def _analyze_error_group(cls, tag: str, entries: List[LogEntry]) -> Dict[str, Any]:
        """分析单个 Tag 的错误组"""
        keywords: set = set()
        error_codes: List[str] = []
        components: List[str] = []
        exception_names: List[str] = []
        error_phrases: List[str] = []
        messages: List[str] = []

        for entry in entries:
            text = entry.message

            for m in cls.KEYWORD_PATTERNS['error_code'].finditer(text):
                code = m.group(1)
                error_codes.append(code)
                keywords.add(f"code:{code}")

            for m in cls.KEYWORD_PATTERNS['component'].finditer(text):
                for comp in (g for g in m.groups() if g):
                    components.append(comp)
                    keywords.add(comp)

            for m in cls.KEYWORD_PATTERNS['exception_name'].finditer(text):
                exc = m.group(1)
                exception_names.append(exc)
                keywords.add(exc)

            for m in cls.KEYWORD_PATTERNS['error_phrase'].finditer(text):
                phrase = m.group(1).strip()
                if len(phrase) > 5:
                    error_phrases.append(phrase)
                    keywords.add(phrase)

            for m in cls.KEYWORD_PATTERNS['message_content'].finditer(text):
                msg = m.group(1).strip()
                if len(msg) > 5:
                    messages.append(msg)

        for part in tag.split('/'):
            if part and len(part) > 2:
                keywords.add(part)

        return {
            'tag': tag,
            'count': len(entries),
            'levels': dict(Counter(e.level for e in entries)),
            'keywords': list(keywords),
            'error_codes': [
                {'code': c, 'count': n}
                for c, n in Counter(error_codes).most_common(5)
            ],
            'components': [
                {'name': c, 'count': n}
                for c, n in Counter(components).most_common(5)
            ],
            'exception_names': [
                {'name': c, 'count': n}
                for c, n in Counter(exception_names).most_common(5)
            ],
            'error_phrases': [
                {'phrase': c, 'count': n}
                for c, n in Counter(error_phrases).most_common(5)
            ],
            'sample_messages': [e.message[:200] for e in entries[:3]],
            'time_range': {
                'first': entries[0].timestamp.isoformat() if entries[0].timestamp else None,
                'last': entries[-1].timestamp.isoformat() if entries[-1].timestamp else None,
            } if entries else None,
        }

    @classmethod
    def _rank_keywords(
        cls, keywords: set, entries: List[LogEntry]
    ) -> List[Dict[str, Any]]:
        """对关键词按重要性排序"""
        scores: List[dict] = []

        for kw in keywords:
            if not kw or len(kw) < 3:
                continue

            count = sum(1 for e in entries if kw.lower() in e.raw_line.lower())
            score = float(count)

            if kw.startswith('code:'):
                score *= 2
            elif kw.endswith('Exception') or kw.endswith('Error'):
                score *= 1.8
            elif kw[0].isupper() and kw.isalnum():
                score *= 1.5
            elif ' ' in kw:
                score *= 1.3

            scores.append({
                'keyword': kw,
                'count': count,
                'score': round(score, 2),
                'type': cls._classify_keyword(kw),
            })

        scores.sort(key=lambda x: x['score'], reverse=True)
        return scores[:20]

    @classmethod
    def _classify_keyword(cls, keyword: str) -> str:
        """分类关键词类型"""
        if keyword.startswith('code:'):
            return 'error_code'
        if keyword.endswith(('Exception', 'Error', 'Failure')):
            return 'exception_name'
        if keyword[0].isupper() and keyword.isalnum() and len(keyword) > 3:
            return 'component'
        if ' ' in keyword:
            return 'error_phrase'
        return 'tag'

    @classmethod
    def analyze(
        cls,
        entries: List[LogEntry],
        analysis_type: str = 'summary',
        custom_regex: Optional[str] = None,
    ) -> Dict[str, Any]:
        """执行日志分析"""
        dispatch = {
            'summary': cls.analyze_summary,
            'errors': cls.analyze_errors,
            'performance': cls.analyze_performance,
            'crashes': cls.analyze_crashes,
            'keywords': cls.analyze_keywords,
        }
        if analysis_type == 'custom' and custom_regex:
            return cls._analyze_custom(entries, custom_regex)
        return dispatch.get(analysis_type, cls.analyze_summary)(entries)

    @classmethod
    def _analyze_custom(
        cls, entries: List[LogEntry], regex_pattern: str
    ) -> Dict[str, Any]:
        """使用自定义正则进行分析"""
        try:
            pattern = re.compile(regex_pattern)
        except re.error as e:
            return {'success': False, 'error': f'无效的正则表达式: {e}'}

        matches: List[dict] = []
        for entry in entries:
            m = pattern.search(entry.raw_line)
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


# ============================================================================
# 内部辅助函数
# ============================================================================

def _clean_dict(d: dict) -> dict:
    """移除字典中值为 None 的键"""
    return {k: v for k, v in d.items() if v is not None}


def _expand_short_time(t: str) -> str:
    """
    将 HH:MM:SS 短格式时间扩展为完整的 YYYY-MM-DD HH:MM:SS。

    处理跨午夜场景：如果扩展后的时间在未来超过1小时，
    说明用户意图是昨天的时间，自动回退一天。
    """
    if len(t) > 8:
        return t
    today = datetime.now()
    candidate = f"{today.strftime('%Y-%m-%d')} {t}"
    try:
        dt = datetime.fromisoformat(candidate)
        if dt > today + timedelta(hours=1):
            yesterday = today - timedelta(days=1)
            candidate = f"{yesterday.strftime('%Y-%m-%d')} {t}"
    except ValueError:
        pass
    return candidate


def _needs_historical_logs(start_time: str, seconds: int) -> bool:
    """判断是否需要从历史落盘文件读取日志（>10 分钟前）"""
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
    if seconds:
        now = datetime.now()
        return {
            'start': (now - timedelta(seconds=seconds)).isoformat(),
            'end': now.isoformat(),
        }
    if start_time or end_time:
        tr: dict = {}
        if start_time:
            tr['start'] = _expand_short_time(start_time)
        if end_time:
            tr['end'] = _expand_short_time(end_time)
        return tr
    return None


def _format_file_size(size: int) -> str:
    """格式化文件大小"""
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / 1024 / 1024:.1f} MB"


def _extract_evidence_lines(entries: List[LogEntry], analysis_type: str) -> List[str]:
    """提取证据行（用于审计）"""
    if analysis_type == 'errors':
        return [e.raw_line for e in entries if e.level in ('E', 'F')][:10]
    if analysis_type == 'crashes':
        lines = []
        for e in entries[:100]:
            if any(p.search(e.raw_line) for p in LogParser.ERROR_PATTERNS.values()):
                lines.append(e.raw_line)
                if len(lines) >= 10:
                    break
        return lines
    if analysis_type == 'keywords':
        return [e.raw_line for e in entries if e.level in ('E', 'F', 'W')][:10]
    return []


def _pull_dict_files(hdc, device: str, local_dir: str) -> Optional[str]:
    """从设备拉取 hilog dict 解密文件（带权限绕过）"""
    list_result = hdc.execute_shell(device, "ls /data/log/hilog/hilog_dict.*.zip 2>/dev/null")
    if not list_result['success'] or not list_result['stdout'].strip():
        logger.info("未找到 hilog dict 文件")
        return None

    dict_files = [
        f.strip() for f in list_result['stdout'].split('\n')
        if f.strip() and 'hilog_dict' in f
    ]
    if not dict_files:
        return None

    tmp_dir = "/data/local/tmp/hilog_dict_tmp"
    hdc.execute_shell(device, f"mkdir -p {tmp_dir}")
    pulled_dicts = []
    try:
        for dict_file in dict_files:
            filename = dict_file.split('/')[-1]
            tmp_path = f"{tmp_dir}/{filename}"
            cp_result = hdc.execute_shell(device, f"cp {dict_file} {tmp_path}")
            if not cp_result['success']:
                logger.warning(f"cp dict 文件失败: {dict_file}")
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
        with zipfile.ZipFile(pulled_dicts[0], 'r') as zf:
            zf.extractall(dict_extract_dir)
        logger.info(f"dict 文件解压到: {dict_extract_dir}")
        return dict_extract_dir
    except Exception as e:
        logger.error(f"dict 文件解压失败: {e}")
        return None


# ============================================================================
# 历史日志获取
# ============================================================================

def _fetch_historical_raw_logs(device, start_time, end_time, max_lines) -> dict:
    """
    从历史 hilog 落盘文件获取原始日志行

    Returns:
        dict with: success, raw_lines, dict_used, files_count, device_id
        On failure: success=False with error/error_code
    """
    hdc = get_hdc()
    hilogtool = get_hilogtool()

    if not hilogtool.is_available():
        return {
            'success': False,
            'error': 'hilogtool 不可用，无法读取历史日志文件',
            'hint': '请设置 HILOGTOOL_PATH 环境变量指向 hilogtool.exe 路径',
            'error_code': 'HILOGTOOL_NOT_AVAILABLE',
            'logs': [], 'total_lines': 0, 'truncated': False,
        }

    list_result = hdc.list_hilog_files(device)
    if not list_result['success'] or not list_result.get('files'):
        return {
            'success': False, 'device_id': device,
            'error': '未找到历史日志文件', 'error_code': 'NO_HISTORICAL_FILES',
            'logs': [], 'total_lines': 0, 'truncated': False,
        }

    # 解析时间范围
    start_dt = end_dt = None
    if start_time:
        try:
            start_dt = datetime.fromisoformat(_expand_short_time(start_time))
        except ValueError:
            pass
    if end_time:
        try:
            end_dt = datetime.fromisoformat(_expand_short_time(end_time))
        except ValueError:
            pass

    # 创建本地目录
    local_dir = os.path.abspath(
        f"./hilog_files/fetch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    os.makedirs(local_dir, exist_ok=True)

    # 过滤+排序文件
    all_files = [
        f for f in list_result['files']
        if not f['name'].startswith(('hilog_diag.', 'hilog_dict.', 'hilog_kmsg.'))
    ]

    if start_dt or end_dt:
        buffer = timedelta(hours=1)
        matched = []
        for f in all_files:
            fts = f.get('timestamp_dt')
            if not fts:
                matched.append(f)
                continue
            if start_dt and fts < (start_dt - buffer):
                continue
            if end_dt and fts > (end_dt + buffer):
                continue
            matched.append(f)

        target = start_dt
        if start_dt and end_dt:
            target = start_dt + (end_dt - start_dt) / 2
        elif end_dt:
            target = end_dt

        max_dist = timedelta(days=36500)
        matched.sort(
            key=lambda f: abs(f['timestamp_dt'] - target) if f.get('timestamp_dt') else max_dist
        )
        files_to_pull = matched[:5]
    else:
        files_to_pull = all_files[:5]

    if not files_to_pull:
        return {
            'success': False, 'device_id': device,
            'error': f'未找到时间范围 {start_time} ~ {end_time} 内的历史日志文件',
            'error_code': 'NO_MATCHING_FILES',
            'logs': [], 'total_lines': 0, 'truncated': False,
        }

    logger.info(f"匹配到 {len(files_to_pull)} 个历史日志文件: {[f['name'] for f in files_to_pull]}")

    pull_result = hdc.pull_hilog_files(device, files_to_pull, local_dir)
    if not pull_result['success'] or not pull_result.get('pulled_files'):
        return {
            'success': False, 'device_id': device,
            'error': f'拉取历史日志文件失败 (匹配 {len(files_to_pull)} 个文件)',
            'error_code': 'PULL_FILES_FAILED',
            'logs': [], 'total_lines': 0, 'truncated': False,
        }

    # 拉取 dict + 逐文件解密
    dict_path = _pull_dict_files(hdc, device, local_dir)
    all_logs: List[str] = []
    dict_used = False
    cap = min(max_lines * 5, LogSecurityConfig.MAX_LOG_LINES)

    for fi in pull_result['pulled_files']:
        local_path = fi['local_path']
        logger.info(f"解析历史日志文件: {local_path}")
        pr = hilogtool.parse_and_read(local_path, dict_path=dict_path, max_lines=cap - len(all_logs))
        if pr['success']:
            logs = pr.get('logs', [])
            for line in logs[:10]:
                if 'OpenUuidFile fail' in line:
                    logger.warning("hilogtool 输出包含 OpenUuidFile fail 错误，dict 文件可能无效")
                    break
            all_logs.extend(logs)
            if pr.get('dict_used'):
                dict_used = True
        else:
            logger.warning(f"解析文件失败: {local_path}, 错误: {pr.get('error')}")
        if len(all_logs) >= cap:
            break

    if not all_logs:
        return {
            'success': False, 'device_id': device,
            'error': '历史日志文件解析后无内容', 'error_code': 'PARSE_EMPTY',
            'logs': [], 'total_lines': 0, 'truncated': False,
            'dict_used': dict_used, 'files_count': len(pull_result['pulled_files']),
        }

    return {
        'success': True,
        'raw_lines': all_logs,
        'dict_used': dict_used,
        'files_count': len(pull_result['pulled_files']),
        'device_id': device,
    }


# ============================================================================
# 日志保存
# ============================================================================

def _save_logs(output_path, device_id, entries, filters, analysis_result) -> dict:
    """将日志保存到文件"""
    if not output_path:
        output_path = f"./hm_logs/hilog_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    valid, result_path = LogSecurityConfig.validate_save_path(output_path)
    if not valid:
        return {'success': False, 'error': result_path, 'error_code': 'PATH_NOT_ALLOWED'}

    output_dir = os.path.dirname(result_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(result_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("HarmonyOS 日志快照\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"设备ID: {device_id or 'N/A'}\n")
        f.write(f"日志行数: {len(entries)}\n")
        active = {k: v for k, v in filters.items() if v}
        if active:
            f.write(f"过滤条件: {active}\n")
        f.write("=" * 80 + "\n\n")

        if analysis_result and isinstance(analysis_result, dict):
            f.write("--- 分析摘要 ---\n")
            ls = analysis_result.get('level_stats', {})
            if ls:
                f.write(f"级别统计: {ls}\n")
            tr = analysis_result.get('time_range')
            if tr:
                f.write(f"时间范围: {tr.get('start', 'N/A')} ~ {tr.get('end', 'N/A')}\n")
            f.write("\n")

        f.write("--- 日志内容 ---\n\n")
        for entry in entries:
            f.write(entry.raw_line + "\n")

    file_size = os.path.getsize(result_path)
    return {
        'success': True,
        'saved_path': result_path,
        'file_size': file_size,
        'file_size_human': _format_file_size(file_size),
    }


# ============================================================================
# 统一实现
# ============================================================================

def _query_impl(
    device_id=None, logs=None, input_file=None, input_files=None,
    lines=100, level=None, tag=None, keyword=None, pid=None,
    package_name=None, start_time=None, end_time=None, seconds=None,
    analysis_type="summary", custom_regex=None, save_path=None, raw_files=False,
):
    """logs_query 的同步实现（供 asyncio.to_thread 调用）"""
    level = LogParser.normalize_level(level) or level
    filters = _clean_dict({
        'level': level, 'tag': tag, 'keyword': keyword, 'pid': pid,
        'package_name': package_name, 'seconds': seconds,
        'start_time': start_time, 'end_time': end_time,
    })

    # ── raw_files 模式（原 hilog_receive）──────────────────────
    if raw_files:
        try:
            hdc = get_hdc()
            ok, device = ToolBase.get_device_id(device_id)
            if not ok:
                device.setdefault('files', [])
                device.setdefault('total_size', 0)
                return device
            result = hdc.hilog_receive(device, save_path)
            result['device_id'] = device
            result.setdefault('files', [])
            result.setdefault('total_size', 0)
            return result
        except Exception as e:
            err = ToolBase.wrap_error(e, 'RAW_FILES_ERROR')
            err.update({'files': [], 'total_size': 0})
            return err

    # ── 获取原始日志行 ──────────────────────────────────────────
    try:
        raw_lines: Optional[List[str]] = None
        _device_id = device_id
        source = 'direct'
        extra: dict = {}

        if logs:
            raw_lines = logs
            source = 'direct'
        elif input_file or input_files:
            paths = list(input_files or [])
            if input_file and input_file not in paths:
                paths.append(input_file)
            all_lines: List[str] = []
            for fpath in paths:
                if not os.path.isfile(fpath):
                    return {
                        'success': False, 'error': f'文件不存在: {fpath}',
                        'error_code': 'FILE_NOT_FOUND',
                        'logs': [], 'total_lines': 0, 'truncated': False,
                        'filters_applied': filters,
                    }
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                        all_lines.extend(f.read().splitlines())
                except OSError as e:
                    return {
                        'success': False, 'error': f'读取文件失败: {fpath}: {e}',
                        'error_code': 'FILE_READ_ERROR',
                        'logs': [], 'total_lines': 0, 'truncated': False,
                        'filters_applied': filters,
                    }
            raw_lines = all_lines
            source = 'file'
        else:
            # 从设备获取
            hdc = get_hdc()
            ok, device = ToolBase.get_device_id(_device_id)
            if not ok:
                device.update({
                    'logs': [], 'total_lines': 0, 'truncated': False,
                    'filters_applied': filters,
                })
                return device
            _device_id = device

            if _needs_historical_logs(start_time, seconds):
                source = 'persist_file'
                logger.info("检测到历史时间范围，切换到历史文件读取模式")
                hist = _fetch_historical_raw_logs(device, start_time, end_time, lines)
                if not hist['success']:
                    hist['filters_applied'] = filters
                    return hist
                raw_lines = hist['raw_lines']
                extra['dict_used'] = hist.get('dict_used', False)
                extra['files_count'] = hist.get('files_count', 0)
            else:
                source = 'realtime_buffer'
                resolved_pid = pid
                if package_name and not pid:
                    app_pid = hdc.get_app_pid(device, package_name)
                    if app_pid:
                        resolved_pid = app_pid
                        logger.info(f"通过包名 {package_name} 解析到 PID: {app_pid}")
                    else:
                        return {
                            'success': False, 'device_id': device,
                            'error': f'应用 {package_name} 未运行或未找到进程',
                            'hint': '请确保应用已启动', 'error_code': 'APP_NOT_RUNNING',
                            'logs': [], 'total_lines': 0, 'truncated': False,
                            'filters_applied': filters,
                        }
                fetch_n = min(lines * 5, LogSecurityConfig.MAX_LOG_LINES)
                log_text = hdc.get_realtime_logs(device, lines=fetch_n, tag=tag, pid=resolved_pid)
                raw_lines = log_text.split('\n') if log_text else []

        # ── 解析 ─────────────────────────────────────────────────
        entries = LogParser.parse_logs(raw_lines or [])

        # ── 过滤 ─────────────────────────────────────────────────
        time_range = _build_time_range(seconds, start_time, end_time)
        filtered = LogParser.filter_entries(
            entries, level=level, tag=tag, keyword=keyword,
            time_range=time_range, pid=pid, seconds=seconds,
        )
        if package_name and source != 'realtime_buffer':
            pkg = package_name.lower()
            filtered = [e for e in filtered if pkg in e.raw_line.lower()]

        # ── 截断 ─────────────────────────────────────────────────
        max_n = min(lines, LogSecurityConfig.MAX_LOG_LINES)
        truncated = len(filtered) > max_n
        filtered = filtered[:max_n]

        # ── 分析 ─────────────────────────────────────────────────
        analysis_result = LogParser.analyze(filtered, analysis_type, custom_regex)
        evidence = _extract_evidence_lines(filtered, analysis_type)

        # ── 保存 ─────────────────────────────────────────────────
        saved = None
        if save_path is not None:
            saved = _save_logs(save_path, _device_id, filtered, filters, analysis_result)

        # ── 构造返回 ─────────────────────────────────────────────
        result: dict = {
            'success': True,
            'device_id': _device_id or '',
            'source': source,
            'logs': [e.raw_line for e in filtered],
            'total_lines': len(filtered),
            'truncated': truncated,
            'filters_applied': _clean_dict(filters),
            'analysis_type': analysis_type,
            'analysis': analysis_result,
            'evidence_lines': evidence,
            'total_entries_analyzed': len(filtered),
        }
        result.update(extra)

        if saved and saved['success']:
            result['saved_path'] = saved['saved_path']
            result['file_size'] = saved['file_size']
            result['file_size_human'] = saved['file_size_human']

        return result

    except Exception as e:
        err = ToolBase.wrap_error(e, 'LOG_QUERY_ERROR')
        err.update({
            'logs': [], 'total_lines': 0, 'truncated': False,
            'filters_applied': filters,
        })
        return err


# ============================================================================
# MCP 工具
# ============================================================================

@mcp_tool(category="general")
async def logs_query(
    device_id: Optional[str] = None,
    logs: Optional[List[str]] = None,
    input_file: Optional[str] = None,
    input_files: Optional[List[str]] = None,
    lines: int = 100,
    level: Optional[str] = None,
    tag: Optional[str] = None,
    keyword: Optional[str] = None,
    pid: Optional[int] = None,
    package_name: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    seconds: Optional[int] = None,
    analysis_type: str = "summary",
    custom_regex: Optional[str] = None,
    save_path: Optional[str] = None,
    raw_files: bool = False,
) -> LogsQueryResult:
    """
    统一日志查询工具 - 拉取 / 解析 / 过滤 / 分析 / 保存 一体化

    数据来源（按优先级）:
    1. logs 参数直接传入日志行列表
    2. input_file / input_files 指定本地文件
    3. 从设备获取（自动判断实时缓冲区 or 历史落盘文件）

    特殊模式:
    - raw_files=True: 直接从设备拉取原始 hilog 日志文件和 dict 解密文件（不解析）

    Args:
        device_id: 设备ID，如果为None则使用第一个设备
        logs: 日志行列表（直接传入则跳过设备获取）
        input_file: 本地日志文件路径（单文件）
        input_files: 本地日志文件路径列表（多文件，合并分析）
        lines: 最大返回行数（默认100，最大50000）
        level: 日志级别过滤 (D/I/W/E/F)，返回该级别及以上
        tag: Tag 过滤（模糊匹配）
        keyword: 关键字过滤（在日志内容中搜索）
        pid: 进程ID过滤
        package_name: 应用包名过滤（如 com.example.myapplication），自动获取应用PID
        start_time: 开始时间（格式：HH:MM:SS 或 YYYY-MM-DD HH:MM:SS）
        end_time: 结束时间（格式：HH:MM:SS 或 YYYY-MM-DD HH:MM:SS）
        seconds: 获取最近N秒内的日志（与start_time/end_time互斥）
        analysis_type: 分析类型
            - summary: 摘要统计（级别分布、Top Tags、时间范围）
            - errors: 错误分析（E/F级别日志分组、异常类型识别）
            - performance: 性能分析（提取耗时数据、统计指标）
            - crashes: 崩溃分析（Crash/ANR/Exception 识别）
            - keywords: 关键词提取（提取错误码、组件名、异常名、报错短语）
            - custom: 自定义正则匹配
        custom_regex: 自定义正则表达式（仅 analysis_type=custom 时使用）
        save_path: 保存路径（指定后将日志快照写入文件）
        raw_files: 是否直接拉取原始日志文件（不解析，用于离线分析）

    Returns:
        统一查询结果，包含日志内容、过滤信息、分析结果和保存路径
    """
    return await asyncio.to_thread(
        _query_impl,
        device_id=device_id, logs=logs, input_file=input_file,
        input_files=input_files, lines=lines, level=level, tag=tag,
        keyword=keyword, pid=pid, package_name=package_name,
        start_time=start_time, end_time=end_time, seconds=seconds,
        analysis_type=analysis_type, custom_regex=custom_regex,
        save_path=save_path, raw_files=raw_files,
    )