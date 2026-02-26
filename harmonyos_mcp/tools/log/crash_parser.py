"""
崩溃日志解析器模块

解析 HarmonyOS 崩溃日志（cppcrash/jscrash/appfreeze）
"""
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any


@dataclass
class CrashBacktrace:
    pc: str
    lib: str
    func: Optional[str] = None
    offset: Optional[str] = None


@dataclass
class CrashThread:
    tid: int
    name: str
    backtrace: List[CrashBacktrace]


@dataclass
class CrashInfo:
    crash_type: str
    file_name: str
    timestamp: Optional[datetime] = None
    module_name: Optional[str] = None
    version: Optional[str] = None
    pid: Optional[int] = None
    uid: Optional[int] = None
    process_name: Optional[str] = None
    reason: Optional[str] = None
    fault_thread: Optional[CrashThread] = None
    other_threads: List[CrashThread] = None
    summary: Optional[str] = None
    raw_content: str = ""

    def __post_init__(self):
        if self.other_threads is None:
            self.other_threads = []


class CrashParser:
    cppcrash_pattern = re.compile(
        r'^cppcrash-(?P<package>[\w\.]+)-(?P<uid>\d+)-(?P<timestamp>\d+)\.log$'
    )
    jscrash_pattern = re.compile(
        r'^jscrash-(?P<package>[\w\.]+)-(?P<uid>\d+)-(?P<timestamp>\d+)\.log$'
    )
    appfreeze_pattern = re.compile(
        r'^appfreeze-(?P<package>[\w\.]+)-(?P<uid>\d+)-(?P<timestamp>\d+)\.log$'
    )

    @classmethod
    def parse_filename(cls, filename: str) -> Optional[Dict[str, Any]]:
        name = Path(filename).name
        for pattern, crash_type in [
            (cls.cppcrash_pattern, 'cppcrash'),
            (cls.jscrash_pattern, 'jscrash'),
            (cls.appfreeze_pattern, 'appfreeze'),
        ]:
            m = pattern.match(name)
            if m:
                ts_str = m.group('timestamp')
                try:
                    ts = datetime.strptime(ts_str, '%Y%m%d%H%M%S%f')
                except ValueError:
                    ts = None
                return {
                    'type': crash_type,
                    'package': m.group('package'),
                    'uid': int(m.group('uid')),
                    'timestamp': ts,
                    'filename': name,
                }
        return None

    @classmethod
    def parse_cppcrash(cls, content: str, filename: str = "") -> CrashInfo:
        info = CrashInfo(crash_type='cppcrash', file_name=filename, raw_content=content)
        lines = content.split('\n')

        for line in lines[:30]:
            if line.startswith('Module name:'):
                info.module_name = line.split(':', 1)[1].strip()
            elif line.startswith('Version:'):
                info.version = line.split(':', 1)[1].strip()
            elif line.startswith('Timestamp:'):
                try:
                    info.timestamp = datetime.strptime(line.split(':', 1)[1].strip(), '%Y-%m-%d %H:%M:%S.%f')
                except ValueError:
                    pass
            elif line.startswith('Pid:'):
                try:
                    info.pid = int(line.split(':', 1)[1].strip())
                except ValueError:
                    pass
            elif line.startswith('Uid:'):
                try:
                    info.uid = int(line.split(':', 1)[1].strip())
                except ValueError:
                    pass
            elif line.startswith('Process name:'):
                info.process_name = line.split(':', 1)[1].strip()
            elif line.startswith('Reason:'):
                info.reason = line.split(':', 1)[1].strip()

        fault_thread = cls._parse_fault_thread(content)
        if fault_thread:
            info.fault_thread = fault_thread

        info.summary = cls._generate_summary(info)

        return info

    @classmethod
    def _parse_fault_thread(cls, content: str) -> Optional[CrashThread]:
        in_fault = False
        tid = None
        name = None
        backtrace = []

        backtrace_pattern = re.compile(
            r'^#(?P<frame>\d+)\s+pc\s+(?P<pc>[0-9a-fA-F]+)\s+(?P<lib>[^\s]+)(?:\((?P<func>[^\)]+)\))?'
        )

        for line in content.split('\n'):
            if line.startswith('Fault thread info:'):
                in_fault = True
                continue
            if in_fault and line.startswith('Other thread info:'):
                break
            if in_fault:
                if line.startswith('Tid:'):
                    parts = line.split(',')
                    try:
                        tid = int(parts[0].split(':')[1].strip())
                    except (ValueError, IndexError):
                        pass
                    if ',' in line and 'Name:' in line:
                        name = line.split('Name:')[1].strip()
                else:
                    m = backtrace_pattern.match(line.strip())
                    if m:
                        func_str = m.group('func') or ''
                        func_name = None
                        offset = None
                        if func_str:
                            if '+' in func_str:
                                parts = func_str.rsplit('+', 1)
                                func_name = parts[0]
                                offset = parts[1] if len(parts) > 1 else None
                            else:
                                func_name = func_str
                        backtrace.append(CrashBacktrace(
                            pc=m.group('pc'),
                            lib=m.group('lib'),
                            func=func_name,
                            offset=offset
                        ))

        if tid or backtrace:
            return CrashThread(tid=tid or 0, name=name or '', backtrace=backtrace)
        return None

    @classmethod
    def _generate_summary(cls, info: CrashInfo) -> str:
        parts = []
        if info.reason:
            parts.append(f"原因: {info.reason}")
        if info.fault_thread and info.fault_thread.backtrace:
            first_frame = info.fault_thread.backtrace[0]
            if first_frame.func:
                parts.append(f"位置: {first_frame.func} ({first_frame.lib})")
            else:
                parts.append(f"位置: {first_frame.lib}")
        return " | ".join(parts) if parts else "崩溃原因未知"

    @classmethod
    def parse(cls, content: str, filename: str = "") -> Optional[CrashInfo]:
        file_info = cls.parse_filename(filename)
        if not file_info:
            return None

        crash_type = file_info['type']
        if crash_type == 'cppcrash':
            return cls.parse_cppcrash(content, filename)
        elif crash_type == 'jscrash':
            return cls.parse_cppcrash(content, filename)
        elif crash_type == 'appfreeze':
            return cls.parse_cppcrash(content, filename)
        return None

    @classmethod
    def match_crash_files(
        cls,
        file_list: List[str],
        package_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        matched = []
        for f in file_list:
            info = cls.parse_filename(f)
            if not info:
                continue
            if package_name and info['package'] != package_name:
                continue
            if start_time and info['timestamp'] and info['timestamp'] < start_time:
                continue
            if end_time and info['timestamp'] and info['timestamp'] > end_time:
                continue
            matched.append(info)
        matched.sort(key=lambda x: x['timestamp'] or datetime.min, reverse=True)
        return matched

    @classmethod
    def to_dict(cls, info: CrashInfo) -> Dict[str, Any]:
        result = {
            'type': info.crash_type,
            'file': info.file_name,
            'timestamp': info.timestamp.isoformat() if info.timestamp else None,
            'module_name': info.module_name,
            'version': info.version,
            'pid': info.pid,
            'uid': info.uid,
            'process_name': info.process_name,
            'reason': info.reason,
            'summary': info.summary,
        }
        if info.fault_thread:
            result['fault_thread'] = {
                'tid': info.fault_thread.tid,
                'name': info.fault_thread.name,
                'backtrace': [
                    {
                        'pc': bt.pc,
                        'lib': bt.lib,
                        'func': bt.func,
                        'offset': bt.offset,
                    }
                    for bt in info.fault_thread.backtrace[:10]
                ]
            }
        return result
