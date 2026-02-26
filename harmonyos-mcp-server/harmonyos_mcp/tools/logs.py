"""
日志查询工具

合并原有 hilog_receive / logs_fetch / logs_save_snapshot / logs_analyze
为单一 logs_query 工具，实现 拉取 -> 解析 -> 过滤 -> 分析 -> 保存 一体化流程。
"""
import asyncio
import os
import re
import zipfile
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from loguru import logger

from ..container import get_hdc, get_hilogtool
from ..config import LogSecurityConfig
from ..types import LogsQueryResult
from .base import ToolBase
from .registry import mcp_tool

LOG_FETCH_MULTIPLIER = 5


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
                        ts = datetime.strptime(
                            f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S.%f"
                        )
                        # 跨年修正：如果解析出的时间在未来超过1天，回退到去年
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
        seconds: Optional[int] = None,
        package_name: Optional[str] = None,
    ) -> List[LogEntry]:
        """过滤日志条目（单趟遍历）"""
        # 预计算过滤条件
        min_p = None
        if level:
            normalized = cls.normalize_level(level)
            min_p = cls.PRIO_MAP.get(normalized, 0) if normalized else 0

        tag_lower = tag.lower() if tag else None
        kw_lower = keyword.lower() if keyword else None
        pkg_lower = package_name.lower() if package_name else None

        start_dt = end_dt = None
        if time_range:
            start_dt = time_range.get('start')
            end_dt = time_range.get('end')

        cutoff = None
        if seconds:
            cutoff = datetime.now() - timedelta(seconds=seconds)

        # 单趟遍历
        result = []
        for entry in entries:
            if min_p is not None:
                if not entry.level or cls.PRIO_MAP.get(entry.level.upper(), 0) < min_p:
                    continue
            if tag_lower:
                if not entry.tag or tag_lower not in entry.tag.lower():
                    continue
            if kw_lower:
                if kw_lower not in entry.message.lower() and kw_lower not in entry.raw_line.lower():
                    continue
            if pid:
                if entry.pid != pid:
                    continue
            if start_dt:
                if not entry.timestamp or entry.timestamp < start_dt:
                    continue
            if end_dt:
                if not entry.timestamp or entry.timestamp > end_dt:
                    continue
            if cutoff:
                if not entry.timestamp or entry.timestamp < cutoff:
                    continue
            if pkg_lower:
                if pkg_lower not in entry.raw_line.lower():
                    continue
            if cls._is_noise(entry):
                continue
            result.append(entry)
        return result

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
    def analyze(
        cls,
        entries: List[LogEntry],
        analysis_type: str = 'summary',
        custom_regex: Optional[str] = None,
    ) -> Dict[str, Any]:
        """执行日志分析（仅支持 summary 和 custom）"""
        if analysis_type == 'custom' and custom_regex:
            return cls._analyze_custom(entries, custom_regex)
        return cls.analyze_summary(entries)

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


# ============================================================================
# 内部辅助函数
# ============================================================================

def _clean_dict(d: dict) -> dict:
    """移除字典中值为 None 的键"""
    return {k: v for k, v in d.items() if v is not None}


def _parse_time_expr(expr: str) -> Optional[Dict[str, datetime]]:
    """
    解析自然语言时间表达式为 start/end datetime 字典。

    支持格式：
    - 相对时间：最近N分钟/小时/秒
    - 日期词：今天/昨天/前天/N天前
    - 时段词：上午/下午/晚上/凌晨/中午
    - 组合：昨天上午、前天晚上、3天前下午

    Returns:
        {'start': datetime, 'end': datetime} 或 None（无法解析）
    """
    if not expr or not expr.strip():
        return None

    expr = expr.strip()
    now = datetime.now()

    # --- 相对时间：最近N分钟/小时/秒 ---
    m = re.match(r'最近\s*(\d+)\s*(分钟|小时|秒|天)', expr)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        delta_map = {'秒': timedelta(seconds=n), '分钟': timedelta(minutes=n),
                     '小时': timedelta(hours=n), '天': timedelta(days=n)}
        delta = delta_map.get(unit)
        if delta:
            return {'start': now - delta, 'end': now}

    # --- 解析日期部分 ---
    base_date = None  # type: Optional[datetime]
    remaining = expr

    # N天前
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

    # --- 解析时段部分 ---
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

    # --- 组合结果 ---
    if base_date is None and period_start is None:
        return None  # 无法解析

    if base_date is None:
        # 仅有时段，默认今天
        base_date = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if period_start is not None:
        start = base_date.replace(hour=period_start)
        end_hour = min(period_end, 23)
        end = base_date.replace(hour=end_hour, minute=59, second=59)
    else:
        # 仅有日期，取全天
        start = base_date
        end = base_date.replace(hour=23, minute=59, second=59)

    # 如果结束时间在未来，截断到当前
    if end > now:
        end = now

    return {'start': start, 'end': end}


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
    """构建时间范围过滤条件（返回 datetime 对象，避免字符串转换）"""
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

        # 按时间排序，拉取范围内的全部文件（上限 15 个）
        matched.sort(
            key=lambda f: f['timestamp_dt'] if f.get('timestamp_dt') else datetime.min
        )
        files_to_pull = matched[:15]
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
    cap = min(max_lines * LOG_FETCH_MULTIPLIER, LogSecurityConfig.MAX_LOG_LINES)

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
    analysis_type="summary", custom_regex=None, save_path=None,
    time_expr=None,
):
    """logs_query 的同步实现（供 asyncio.to_thread 调用）"""

    # ── 自然语言时间解析（优先级低于显式 start_time/end_time/seconds）──
    if time_expr and not start_time and not end_time and not seconds:
        parsed = _parse_time_expr(time_expr)
        if parsed:
            start_time = parsed['start'].strftime('%Y-%m-%d %H:%M:%S')
            end_time = parsed['end'].strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"time_expr '{time_expr}' -> {start_time} ~ {end_time}")

    filters = _clean_dict({
        'level': level, 'tag': tag, 'keyword': keyword, 'pid': pid,
        'package_name': package_name, 'seconds': seconds,
        'start_time': start_time, 'end_time': end_time,
    })

    # ── 获取原始日志行 ──────────────────────────────────────────
    try:
        raw_lines: Optional[List[str]] = None
        _device_id = device_id
        source = 'direct'
        extra: dict = {}

        if logs:
            raw_lines = logs
        elif input_file or input_files:
            paths = list(input_files or [])
            if input_file and input_file not in paths:
                paths.append(input_file)
            all_lines: List[str] = []
            MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB
            for fpath in paths:
                if not os.path.isfile(fpath):
                    return {
                        'success': False, 'error': f'文件不存在: {fpath}',
                        'error_code': 'FILE_NOT_FOUND',
                        'logs': [], 'total_lines': 0, 'truncated': False,
                        'filters_applied': filters,
                    }
                file_size = os.path.getsize(fpath)
                if file_size > MAX_FILE_SIZE:
                    return {
                        'success': False,
                        'error': f'文件过大: {fpath} ({_format_file_size(file_size)})，上限 200MB',
                        'error_code': 'FILE_TOO_LARGE',
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
                fetch_n = min(lines * LOG_FETCH_MULTIPLIER, LogSecurityConfig.MAX_LOG_LINES)
                log_text = hdc.get_realtime_logs(device, lines=fetch_n, tag=tag, pid=resolved_pid)
                raw_lines = log_text.split('\n') if log_text else []

        # ── 解析 ─────────────────────────────────────────────────
        entries = LogParser.parse_logs(raw_lines or [])

        # ── 过滤 ─────────────────────────────────────────────────
        time_range = _build_time_range(seconds, start_time, end_time)
        pkg_filter = package_name if (package_name and source != 'realtime_buffer') else None
        filtered = LogParser.filter_entries(
            entries, level=level, tag=tag, keyword=keyword,
            time_range=time_range, pid=pid, seconds=seconds,
            package_name=pkg_filter,
        )

        # ── 截断 ─────────────────────────────────────────────────
        max_n = min(lines, LogSecurityConfig.MAX_LOG_LINES)
        truncated = len(filtered) > max_n
        filtered = filtered[:max_n]

        # ── 分析 ─────────────────────────────────────────────────
        analysis_result = LogParser.analyze(filtered, analysis_type, custom_regex)

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
    time_expr: Optional[str] = None,
) -> LogsQueryResult:
    """
    统一日志查询工具 - 拉取 / 解析 / 过滤 / 分析 / 保存 一体化

    数据来源（按优先级）:
    1. logs 参数直接传入日志行列表
    2. input_file / input_files 指定本地文件
    3. 从设备获取（自动判断实时缓冲区 or 历史落盘文件）

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
            - custom: 自定义正则匹配
        custom_regex: 自定义正则表达式（仅 analysis_type=custom 时使用）
        save_path: 保存路径（指定后将日志快照写入文件）
        time_expr: 自然语言时间表达式（如"昨天上午"、"最近5分钟"、"前天晚上"），
                   优先级低于 start_time/end_time/seconds

    Returns:
        统一查询结果，包含日志内容、过滤信息、分析结果和保存路径

    HarmonyOS 常见错误模式参考（用于分析返回的日志内容）:

        Crash 崩溃:
            - 关键词: fatal signal, Native crash
            - 排查: 堆栈分析、内存越界、空指针

        ANR 无响应:
            - 关键词: ANR in
            - 排查: 主线程阻塞、死锁、耗时操作

        JS/ArkTS 错误:
            - 关键词: JsHeapObject, JavaScript runtime error, ArkTS runtime error
            - 排查: 变量未初始化、类型错误、异步处理

        权限错误:
            - 关键词: Permission denied
            - 排查: module.json5 权限配置、运行时权限申请

        网络错误:
            - 关键词: network error
            - 排查: INTERNET 权限、证书配置、网络连通性

        内存错误:
            - 关键词: OutOfMemory, OOM, malloc failed, allocation failed
            - 排查: 内存泄漏、大对象、Bitmap 未回收

        UI 错误:
            - 关键词: Window load failed, loadContent.*failed, Layout inflate error
            - 排查: main_pages.json 配置、页面路径拼写、组件初始化

        启动错误:
            - 关键词: Ability.*start failed, EntryAbility.*error, main_pages.*not found
            - 排查: Ability 配置、入口页面路径

        资源错误:
            - 关键词: Resource not found, rawfile.*not exist
            - 排查: 资源路径、rawfile 目录、打包配置

        IPC 错误:
            - 关键词: IPC.*failed, Binder.*died
            - 排查: 服务连接、进程间通信

        数据库错误:
            - 关键词: database.*error, SQL.*exception
            - 排查: 数据库版本、SQL 语法、事务处理

        签名/证书错误:
            - 关键词: signature.*failed, certificate.*invalid
            - 排查: 签名配置、证书有效期

    系统噪声过滤（已自动忽略）:
        - /sys/power/last_sr, XCollie, logd prune, healthd, chatty
        - ServiceManager: Waiting, suspend/resume, Watchdog, GC, Choreographer
    """
    return await asyncio.to_thread(
        _query_impl,
        device_id=device_id, logs=logs, input_file=input_file,
        input_files=input_files, lines=lines, level=level, tag=tag,
        keyword=keyword, pid=pid, package_name=package_name,
        start_time=start_time, end_time=end_time, seconds=seconds,
        analysis_type=analysis_type, custom_regex=custom_regex,
        save_path=save_path, time_expr=time_expr,
    )