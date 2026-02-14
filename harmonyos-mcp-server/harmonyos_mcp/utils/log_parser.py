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
    
    # 级别名称到单字符的映射（支持各种常见写法）
    LEVEL_NAME_MAP = {
        'D': 'D', 'DEBUG': 'D',
        'I': 'I', 'INFO': 'I',
        'W': 'W', 'WARN': 'W', 'WARNING': 'W',
        'E': 'E', 'ERROR': 'E',
        'F': 'F', 'FATAL': 'F',
    }

    # 错误/异常模式
    ERROR_PATTERNS = {
        'exception': re.compile(r'(?i)(exception|error|fail|crash)', re.IGNORECASE),
        'anr': re.compile(r'(?i)(anr|application not responding)', re.IGNORECASE),
        'crash': re.compile(r'(?i)(crash|fatal|abort|segfault|sigsegv)', re.IGNORECASE),
        'oom': re.compile(r'(?i)(out\s*of\s*memory|oom|memory\s*allocation\s*failed)', re.IGNORECASE),
        'timeout': re.compile(r'(?i)(timeout|timed?\s*out)', re.IGNORECASE),
    }
    
    # 系统噪声日志模式（在错误分析中自动过滤）
    NOISE_PATTERNS = [
        re.compile(r'/sys/power/last_sr'),                    # XCollie 看门狗系统文件读取
        re.compile(r'XCollie.*last_sr'),                      # XCollie 相关
        re.compile(r'Failed to read file:\s*/sys/'),          # /sys/ 系统目录读取失败
    ]
    
    @classmethod
    def _is_noise(cls, entry: LogEntry) -> bool:
        """检查日志条目是否为系统噪声"""
        text = entry.message or entry.raw_line
        return any(p.search(text) for p in cls.NOISE_PATTERNS)
    
    # 关键词提取模式
    KEYWORD_PATTERNS = {
        # 错误码提取: code: 401, error=123, errno:-1
        'error_code': re.compile(r'(?:code|error|errno|status|ret|result)\s*[:=]\s*(-?\d+)', re.IGNORECASE),
        # 系统组件: [window][loadContent], <ComponentName>
        'component': re.compile(r'\[(\w+)\]\[(\w+)\]|\[([A-Z][a-zA-Z]+)\]|<([A-Z][a-zA-Z]+)>'),
        # 异常类名: NullPointerException, IOException
        'exception_name': re.compile(r'\b([A-Z][a-zA-Z]*(?:Exception|Error|Failure|Fault))\b'),
        # 核心报错短语: Failed to xxx, Unable to xxx, Cannot xxx
        'error_phrase': re.compile(r'((?:Failed|Unable|Cannot|Could not|Couldn\'t|Error|Fail)\s+to\s+[\w\s]+?)(?:\.|,|$|Cause)', re.IGNORECASE),
        # 消息前缀: msg:, message:, reason:
        'message_content': re.compile(r'(?:msg|message|reason|cause)\s*[:=]\s*([^,\n\.]+)', re.IGNORECASE),
    }
    
    # 性能相关模式
    PERF_PATTERNS = {
        'duration': re.compile(r'(?i)(cost|duration|elapsed|time|took|spent)\s*[:\s=]*\s*(\d+(?:\.\d+)?)\s*(ms|s|μs|us|ns)?'),
        'latency': re.compile(r'(?i)latency\s*[:\s=]*\s*(\d+(?:\.\d+)?)\s*(ms|s)?'),
    }
    
    @classmethod
    def normalize_level(cls, level: Optional[str]) -> Optional[str]:
        """
        将各种级别写法归一化为单字符 (D/I/W/E/F)
        
        支持: 'Error'→'E', 'Warning'→'W', 'Info'→'I', 'Debug'→'D', 'Fatal'→'F'
        以及单字符本身 'E'→'E' 等
        
        Args:
            level: 原始级别字符串
            
        Returns:
            归一化后的单字符级别，无法识别时返回 None
        """
        if not level:
            return None
        return cls.LEVEL_NAME_MAP.get(level.strip().upper())

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
        
        # 级别过滤（先归一化，支持 'Error'→'E' 等写法）
        if level:
            normalized = cls.normalize_level(level)
            level_priority = {'D': 0, 'I': 1, 'W': 2, 'E': 3, 'F': 4}
            min_priority = level_priority.get(normalized, 0) if normalized else 0
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
        # 筛选 E/F 级别日志，排除系统噪声
        errors = [
            e for e in entries
            if e.level in ('E', 'F')
            and not cls._is_noise(e)
        ]
        
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
        
        # 检测特定错误类型（同样排除噪声）
        error_types = defaultdict(list)
        for entry in entries:
            if cls._is_noise(entry):
                continue
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
    def analyze_keywords(cls, entries: List[LogEntry]) -> Dict[str, Any]:
        """
        分析日志中的异常并提取可检索关键词
        
        从错误日志中提取：
        - 核心报错文本（如 "Failed to load the content"）
        - 错误码（如 code: 401）
        - 系统组件名（如 [window][loadContent]）
        - 异常类名（如 NullPointerException）
        - 相关 Tag 信息
        
        Args:
            entries: 日志条目列表
            
        Returns:
            关键词提取结果，按异常分组
        """
        # 筛选 E/F/W 级别日志
        error_entries = [e for e in entries if e.level in ('E', 'F', 'W')]
        
        if not error_entries:
            return {
                'total_errors': 0,
                'error_groups': [],
                'search_keywords': [],
                'message': '未发现错误或警告日志'
            }
        
        # 按 Tag 分组异常
        error_groups = defaultdict(list)
        for entry in error_entries:
            tag = entry.tag or 'Unknown'
            error_groups[tag].append(entry)
        
        # 分析每组异常
        analyzed_groups = []
        all_keywords = set()
        
        for tag, group_entries in error_groups.items():
            group_analysis = cls._analyze_error_group(tag, group_entries)
            analyzed_groups.append(group_analysis)
            
            # 收集关键词
            all_keywords.update(group_analysis.get('keywords', []))
        
        # 按错误数量排序
        analyzed_groups.sort(key=lambda x: x['count'], reverse=True)
        
        # 生成搜索关键词列表（去重并按重要性排序）
        search_keywords = cls._rank_keywords(all_keywords, error_entries)
        
        return {
            'total_errors': len(error_entries),
            'error_groups': analyzed_groups,
            'search_keywords': search_keywords,
            'summary': {
                'unique_tags': len(error_groups),
                'error_count': sum(1 for e in error_entries if e.level == 'E'),
                'fatal_count': sum(1 for e in error_entries if e.level == 'F'),
                'warning_count': sum(1 for e in error_entries if e.level == 'W'),
            }
        }
    
    @classmethod
    def _analyze_error_group(cls, tag: str, entries: List[LogEntry]) -> Dict[str, Any]:
        """
        分析单个 Tag 的错误组
        
        Args:
            tag: 日志 Tag
            entries: 该 Tag 下的日志条目
            
        Returns:
            分组分析结果
        """
        keywords = set()
        error_codes = []
        components = []
        exception_names = []
        error_phrases = []
        messages = []
        
        for entry in entries:
            text = entry.message
            raw = entry.raw_line
            
            # 提取错误码
            for match in cls.KEYWORD_PATTERNS['error_code'].finditer(text):
                code = match.group(1)
                error_codes.append(code)
                keywords.add(f"code:{code}")
            
            # 提取系统组件
            for match in cls.KEYWORD_PATTERNS['component'].finditer(text):
                groups = [g for g in match.groups() if g]
                for comp in groups:
                    components.append(comp)
                    keywords.add(comp)
            
            # 提取异常类名
            for match in cls.KEYWORD_PATTERNS['exception_name'].finditer(text):
                exc_name = match.group(1)
                exception_names.append(exc_name)
                keywords.add(exc_name)
            
            # 提取核心报错短语
            for match in cls.KEYWORD_PATTERNS['error_phrase'].finditer(text):
                phrase = match.group(1).strip()
                if len(phrase) > 5:  # 过滤太短的短语
                    error_phrases.append(phrase)
                    keywords.add(phrase)
            
            # 提取消息内容
            for match in cls.KEYWORD_PATTERNS['message_content'].finditer(text):
                msg = match.group(1).strip()
                if len(msg) > 5:
                    messages.append(msg)
        
        # 添加 Tag 本身作为关键词
        tag_parts = tag.split('/')
        for part in tag_parts:
            if part and len(part) > 2:
                keywords.add(part)
        
        # 统计频率
        code_counter = Counter(error_codes)
        component_counter = Counter(components)
        exception_counter = Counter(exception_names)
        phrase_counter = Counter(error_phrases)
        
        return {
            'tag': tag,
            'count': len(entries),
            'levels': dict(Counter(e.level for e in entries)),
            'keywords': list(keywords),
            'error_codes': [
                {'code': code, 'count': cnt}
                for code, cnt in code_counter.most_common(5)
            ],
            'components': [
                {'name': comp, 'count': cnt}
                for comp, cnt in component_counter.most_common(5)
            ],
            'exception_names': [
                {'name': exc, 'count': cnt}
                for exc, cnt in exception_counter.most_common(5)
            ],
            'error_phrases': [
                {'phrase': phrase, 'count': cnt}
                for phrase, cnt in phrase_counter.most_common(5)
            ],
            'sample_messages': [e.message[:200] for e in entries[:3]],
            'time_range': {
                'first': entries[0].timestamp.isoformat() if entries[0].timestamp else None,
                'last': entries[-1].timestamp.isoformat() if entries[-1].timestamp else None,
            } if entries else None
        }
    
    @classmethod
    def _rank_keywords(cls, keywords: set, entries: List[LogEntry]) -> List[Dict[str, Any]]:
        """
        对关键词进行排序，返回最有价值的检索关键词
        
        Args:
            keywords: 关键词集合
            entries: 日志条目列表
            
        Returns:
            排序后的关键词列表
        """
        keyword_scores = []
        
        for kw in keywords:
            if not kw or len(kw) < 3:
                continue
            
            # 计算出现频率
            count = sum(1 for e in entries if kw.lower() in e.raw_line.lower())
            
            # 计算得分：基于长度、是否包含特定模式
            score = count
            
            # 错误码权重高
            if kw.startswith('code:'):
                score *= 2
            # 异常名权重高
            elif kw.endswith('Exception') or kw.endswith('Error'):
                score *= 1.8
            # 组件名权重适中
            elif kw[0].isupper() and kw.isalnum():
                score *= 1.5
            # 短语权重适中
            elif ' ' in kw:
                score *= 1.3
            
            keyword_scores.append({
                'keyword': kw,
                'count': count,
                'score': round(score, 2),
                'type': cls._classify_keyword(kw)
            })
        
        # 按得分排序
        keyword_scores.sort(key=lambda x: x['score'], reverse=True)
        
        return keyword_scores[:20]  # 返回前20个
    
    @classmethod
    def _classify_keyword(cls, keyword: str) -> str:
        """
        分类关键词类型
        
        Args:
            keyword: 关键词
            
        Returns:
            关键词类型
        """
        if keyword.startswith('code:'):
            return 'error_code'
        elif keyword.endswith('Exception') or keyword.endswith('Error') or keyword.endswith('Failure'):
            return 'exception_name'
        elif keyword[0].isupper() and keyword.isalnum() and len(keyword) > 3:
            return 'component'
        elif ' ' in keyword:
            return 'error_phrase'
        else:
            return 'tag'
    
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
            analysis_type: 分析类型 (summary/errors/performance/crashes/keywords/custom)
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
        elif analysis_type == 'keywords':
            return cls.analyze_keywords(entries)
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
