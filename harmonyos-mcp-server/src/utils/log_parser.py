"""
HarmonyOS 日志解析器

提供 hilog 日志的结构化解析、过滤和分析功能
使用正则表达式提取日志字段，不依赖 LLM
"""

import re
import statistics
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from collections import Counter, defaultdict
from loguru import logger


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
        """转换为字典"""
        return {
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'level': self.level,
            'tag': self.tag,
            'pid': self.pid,
            'tid': self.tid,
            'message': self.message,
            'raw_line': self.raw_line
        }


class LogParser:
    """HarmonyOS 日志解析器"""
    
    # 常见日志格式正则（按优先级排列）
    PATTERNS = [
        # 格式1: 01-31 14:30:25.123  1234  5678 I MyApp: message
        # HarmonyOS hilog 标准格式
        re.compile(
            r'^(?P<date>\d{2}-\d{2})\s+'
            r'(?P<time>\d{2}:\d{2}:\d{2}\.\d{3})\s+'
            r'(?P<pid>\d+)\s+'
            r'(?P<tid>\d+)\s+'
            r'(?P<level>[DIWEF])\s+'
            r'(?P<tag>[\w\.\-/]+):\s*'
            r'(?P<message>.*?)$'
        ),
        
        # 格式2: 2026-01-31 14:30:25.123  1234  5678 I MyApp: message
        # 带完整日期的格式
        re.compile(
            r'^(?P<date>\d{4}-\d{2}-\d{2})\s+'
            r'(?P<time>\d{2}:\d{2}:\d{2}\.\d{3})\s+'
            r'(?P<pid>\d+)\s+'
            r'(?P<tid>\d+)\s+'
            r'(?P<level>[DIWEF])\s+'
            r'(?P<tag>[\w\.\-/]+):\s*'
            r'(?P<message>.*?)$'
        ),
        
        # 格式3: [I/MyApp(1234:5678)] message
        # 简化格式
        re.compile(
            r'^\[(?P<level>[DIWEF])/'
            r'(?P<tag>[\w\.\-/]+)'
            r'\((?P<pid>\d+):(?P<tid>\d+)\)\]\s*'
            r'(?P<message>.*?)$'
        ),
        
        # 格式4: I/MyApp(1234): message
        # Android 风格格式
        re.compile(
            r'^(?P<level>[DIWEF])/'
            r'(?P<tag>[\w\.\-/]+)'
            r'\((?P<pid>\d+)\):\s*'
            r'(?P<message>.*?)$'
        ),
        
        # 格式5: [timestamp][PID:TID][LEVEL][TAG] message
        # 另一种结构化格式
        re.compile(
            r'^\[(?P<timestamp>\d+)\]'
            r'\[(?P<pid>\d+):(?P<tid>\d+)\]'
            r'\[(?P<level>[DIWEF])\]'
            r'\[(?P<tag>[\w\.\-/]+)\]\s*'
            r'(?P<message>.*?)$'
        ),
    ]
    
    # 错误/异常模式
    ERROR_PATTERNS = {
        'exception': re.compile(r'(?i)(exception|error|fail|crash)', re.IGNORECASE),
        'anr': re.compile(r'(?i)(anr|application not responding)', re.IGNORECASE),
        'crash': re.compile(r'(?i)(crash|fatal|abort|segfault|sigsegv)', re.IGNORECASE),
        'oom': re.compile(r'(?i)(out\s*of\s*memory|oom|memory\s*allocation\s*failed)', re.IGNORECASE),
        'timeout': re.compile(r'(?i)(timeout|timed?\s*out)', re.IGNORECASE),
    }
    
    # 性能相关模式
    PERF_PATTERNS = {
        'duration': re.compile(r'(?i)(cost|duration|elapsed|time|took|spent)\s*[:\s=]*\s*(\d+(?:\.\d+)?)\s*(ms|s|μs|us|ns)?'),
        'latency': re.compile(r'(?i)latency\s*[:\s=]*\s*(\d+(?:\.\d+)?)\s*(ms|s)?'),
    }
    
    @classmethod
    def parse_line(cls, line: str, year: int = None) -> LogEntry:
        """
        解析单行日志
        
        Args:
            line: 日志行
            year: 年份（用于补全日期），默认使用当前年份
            
        Returns:
            LogEntry 对象
        """
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
                        
                        # 处理 MM-DD 格式，补全年份
                        if len(date_str) == 5:  # MM-DD
                            date_str = f"{year}-{date_str}"
                        
                        datetime_str = f"{date_str} {time_str}"
                        entry.timestamp = datetime.strptime(
                            datetime_str, "%Y-%m-%d %H:%M:%S.%f"
                        )
                    except ValueError:
                        pass
                
                elif 'timestamp' in groups:
                    try:
                        # Unix 时间戳（毫秒）
                        ts = int(groups['timestamp'])
                        entry.timestamp = datetime.fromtimestamp(ts / 1000.0)
                    except (ValueError, OSError):
                        pass
                
                # 解析其他字段
                entry.level = groups.get('level')
                entry.tag = groups.get('tag')
                
                if 'pid' in groups and groups['pid']:
                    try:
                        entry.pid = int(groups['pid'])
                    except ValueError:
                        pass
                
                if 'tid' in groups and groups['tid']:
                    try:
                        entry.tid = int(groups['tid'])
                    except ValueError:
                        pass
                
                entry.message = groups.get('message', '').strip()
                break
        
        # 如果没有匹配任何模式，整行作为 message
        if not entry.level:
            entry.message = line
        
        return entry
    
    @classmethod
    def parse_logs(cls, lines: List[str], year: int = None) -> List[LogEntry]:
        """
        批量解析日志
        
        Args:
            lines: 日志行列表
            year: 年份
            
        Returns:
            LogEntry 对象列表
        """
        return [cls.parse_line(line, year) for line in lines if line.strip()]
    
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
        """
        过滤日志条目
        
        Args:
            entries: 日志条目列表
            level: 日志级别过滤 (D/I/W/E/F)，会过滤出该级别及以上
            tag: Tag 过滤（模糊匹配）
            keyword: 关键字过滤（在 message 中搜索）
            time_range: 时间范围 {"start": "ISO8601", "end": "ISO8601"}
            pid: 进程 ID 过滤
            seconds: 最近 N 秒内的日志
            
        Returns:
            过滤后的日志条目列表
        """
        filtered = entries
        
        # 级别过滤
        if level:
            level_priority = {'D': 0, 'I': 1, 'W': 2, 'E': 3, 'F': 4}
            min_priority = level_priority.get(level.upper(), 0)
            filtered = [
                e for e in filtered
                if e.level and level_priority.get(e.level.upper(), 0) >= min_priority
            ]
        
        # Tag 过滤
        if tag:
            filtered = [
                e for e in filtered
                if e.tag and tag.lower() in e.tag.lower()
            ]
        
        # 关键字过滤
        if keyword:
            filtered = [
                e for e in filtered
                if keyword.lower() in e.message.lower() or keyword.lower() in e.raw_line.lower()
            ]
        
        # PID 过滤
        if pid:
            filtered = [e for e in filtered if e.pid == pid]
        
        # 时间范围过滤
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
        
        # 最近 N 秒过滤
        if seconds:
            cutoff = datetime.now() - timedelta(seconds=seconds)
            filtered = [
                e for e in filtered
                if e.timestamp and e.timestamp >= cutoff
            ]
        
        return filtered
    
    @classmethod
    def analyze_summary(cls, entries: List[LogEntry]) -> Dict[str, Any]:
        """
        生成日志摘要分析
        
        Args:
            entries: 日志条目列表
            
        Returns:
            摘要分析结果
        """
        if not entries:
            return {
                'total_lines': 0,
                'level_stats': {},
                'top_tags': [],
                'top_pids': [],
                'time_range': None
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
                'duration_seconds': (max(timestamps) - min(timestamps)).total_seconds()
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
            'time_range': time_range
        }
    
    @classmethod
    def analyze_errors(cls, entries: List[LogEntry]) -> Dict[str, Any]:
        """
        分析错误日志
        
        Args:
            entries: 日志条目列表
            
        Returns:
            错误分析结果
        """
        # 筛选 E/F 级别日志
        errors = [e for e in entries if e.level in ('E', 'F')]
        
        # 按 tag 分组
        by_tag = defaultdict(list)
        for entry in errors:
            tag = entry.tag or 'Unknown'
            by_tag[tag].append({
                'message': entry.message,
                'timestamp': entry.timestamp.isoformat() if entry.timestamp else None,
                'pid': entry.pid,
                'level': entry.level
            })
        
        # 检测特定错误类型
        error_types = defaultdict(list)
        for entry in entries:
            for error_type, pattern in cls.ERROR_PATTERNS.items():
                if pattern.search(entry.message) or pattern.search(entry.raw_line):
                    error_types[error_type].append({
                        'message': entry.message[:200],  # 截断长消息
                        'timestamp': entry.timestamp.isoformat() if entry.timestamp else None,
                        'tag': entry.tag,
                        'level': entry.level
                    })
        
        return {
            'total_errors': len(errors),
            'error_level_count': sum(1 for e in errors if e.level == 'E'),
            'fatal_level_count': sum(1 for e in errors if e.level == 'F'),
            'by_tag': {
                tag: {
                    'count': len(items),
                    'samples': items[:5]  # 最多返回5个样本
                }
                for tag, items in by_tag.items()
            },
            'error_types': {
                error_type: {
                    'count': len(items),
                    'samples': items[:3]
                }
                for error_type, items in error_types.items()
            }
        }
    
    @classmethod
    def analyze_performance(cls, entries: List[LogEntry]) -> Dict[str, Any]:
        """
        分析性能相关日志
        
        Args:
            entries: 日志条目列表
            
        Returns:
            性能分析结果
        """
        # 提取耗时数据
        durations_ms = []
        perf_logs = []
        
        for entry in entries:
            text = entry.message + ' ' + entry.raw_line
            
            for perf_type, pattern in cls.PERF_PATTERNS.items():
                matches = pattern.findall(text)
                for match in matches:
                    try:
                        if len(match) >= 2:
                            value = float(match[1]) if isinstance(match, tuple) else float(match)
                            unit = match[2] if len(match) > 2 and match[2] else 'ms'
                        else:
                            continue
                        
                        # 统一转换为毫秒
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
                            'timestamp': entry.timestamp.isoformat() if entry.timestamp else None
                        })
                    except (ValueError, TypeError, IndexError):
                        continue
        
        result = {
            'total_perf_logs': len(perf_logs),
            'duration_samples': len(durations_ms),
            'samples': perf_logs[:10]  # 最多返回10个样本
        }
        
        if durations_ms:
            sorted_durations = sorted(durations_ms)
            result['statistics'] = {
                'min_ms': round(min(durations_ms), 2),
                'max_ms': round(max(durations_ms), 2),
                'avg_ms': round(statistics.mean(durations_ms), 2),
                'median_ms': round(statistics.median(durations_ms), 2),
            }
            
            if len(sorted_durations) >= 20:
                result['statistics']['p95_ms'] = round(
                    sorted_durations[int(len(sorted_durations) * 0.95)], 2
                )
                result['statistics']['p99_ms'] = round(
                    sorted_durations[int(len(sorted_durations) * 0.99)], 2
                )
        
        return result
    
    @classmethod
    def analyze_crashes(cls, entries: List[LogEntry]) -> Dict[str, Any]:
        """
        分析崩溃相关日志
        
        Args:
            entries: 日志条目列表
            
        Returns:
            崩溃分析结果
        """
        crashes = []
        anrs = []
        exceptions = []
        
        for entry in entries:
            text = entry.message + ' ' + entry.raw_line
            
            if cls.ERROR_PATTERNS['crash'].search(text):
                crashes.append(entry.to_dict())
            
            if cls.ERROR_PATTERNS['anr'].search(text):
                anrs.append(entry.to_dict())
            
            if cls.ERROR_PATTERNS['exception'].search(text):
                exceptions.append(entry.to_dict())
        
        return {
            'crashes': {
                'count': len(crashes),
                'samples': crashes[:5]
            },
            'anrs': {
                'count': len(anrs),
                'samples': anrs[:5]
            },
            'exceptions': {
                'count': len(exceptions),
                'samples': exceptions[:10]
            },
            'next_steps': cls._generate_next_steps(crashes, anrs, exceptions)
        }
    
    @classmethod
    def _generate_next_steps(cls, crashes: List, anrs: List, exceptions: List) -> List[str]:
        """
        根据日志证据生成下一步排查建议
        
        Returns:
            排查建议列表
        """
        steps = []
        
        if crashes:
            steps.append("发现崩溃日志，建议：1) 检查崩溃堆栈信息 2) 使用 addr2line 解析地址 3) 检查相关内存操作")
        
        if anrs:
            steps.append("发现 ANR 日志，建议：1) 检查主线程阻塞操作 2) 分析 trace 文件 3) 检查 Binder 调用超时")
        
        if exceptions:
            steps.append("发现异常日志，建议：1) 检查异常堆栈 2) 确认异常触发条件 3) 检查相关输入参数")
        
        if not steps:
            steps.append("未发现明显的崩溃或异常模式")
        
        return steps
    
    @classmethod
    def analyze(
        cls,
        entries: List[LogEntry],
        analysis_type: str = 'summary',
        custom_regex: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行日志分析
        
        Args:
            entries: 日志条目列表
            analysis_type: 分析类型 (summary/errors/performance/crashes/custom)
            custom_regex: 自定义正则表达式（仅 custom 类型使用）
            
        Returns:
            分析结果
        """
        if analysis_type == 'summary':
            return cls.analyze_summary(entries)
        elif analysis_type == 'errors':
            return cls.analyze_errors(entries)
        elif analysis_type == 'performance':
            return cls.analyze_performance(entries)
        elif analysis_type == 'crashes':
            return cls.analyze_crashes(entries)
        elif analysis_type == 'custom' and custom_regex:
            return cls._analyze_custom(entries, custom_regex)
        else:
            return cls.analyze_summary(entries)
    
    @classmethod
    def _analyze_custom(cls, entries: List[LogEntry], regex_pattern: str) -> Dict[str, Any]:
        """
        使用自定义正则进行分析
        
        Args:
            entries: 日志条目列表
            regex_pattern: 正则表达式
            
        Returns:
            匹配结果
        """
        try:
            pattern = re.compile(regex_pattern)
        except re.error as e:
            return {
                'success': False,
                'error': f'无效的正则表达式: {e}'
            }
        
        matches = []
        for entry in entries:
            match = pattern.search(entry.raw_line)
            if match:
                matches.append({
                    'line': entry.raw_line,
                    'groups': match.groups(),
                    'groupdict': match.groupdict(),
                    'timestamp': entry.timestamp.isoformat() if entry.timestamp else None
                })
        
        return {
            'success': True,
            'pattern': regex_pattern,
            'total_matches': len(matches),
            'matches': matches[:100]  # 最多返回100个匹配
        }
