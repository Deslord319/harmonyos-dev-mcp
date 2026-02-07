"""
日志分析工具

提供日志获取、保存快照、结构化分析等功能。
"""
import os
from datetime import datetime, timedelta
from typing import Optional, List
from loguru import logger

from ..container import get_hdc
from ..config import LogSecurityConfig
from ..utils.log_parser import LogParser, LogEntry
from ..types import LogsFetchResult, LogsSaveResult, LogsAnalyzeResult, AnalysisType
from .base import ToolBase


def _empty_filters() -> dict:
    """返回空的过滤配置"""
    return {
        'level': None,
        'tag': None,
        'keyword': None,
        'pid': None,
        'time_range': None,
        'seconds': None
    }


def _empty_summary() -> dict:
    """返回空的摘要"""
    return {
        'level_stats': {},
        'time_range': None
    }


def _logs_fetch_impl(
    device_id: str = None,
    lines: int = 100,
    level: str = None,
    tag: str = None,
    keyword: str = None,
    pid: int = None,
    package_name: str = None,
    start_time: str = None,
    end_time: str = None,
    seconds: int = None
) -> dict:
    """
    日志获取的内部实现（供工具函数调用）

    Args:
        package_name: 应用包名，如果指定则自动获取该应用的PID进行过滤
    """
    # 构建过滤配置（用于所有返回路径）
    filters = {
        'level': level,
        'tag': tag,
        'keyword': keyword,
        'pid': pid,
        'time_range': None,
        'seconds': seconds
    }
    
    try:
        hdc = get_hdc()

        # 获取设备
        ok, device = ToolBase.get_device_id(device_id)
        if not ok:
            device['logs'] = []
            device['total_lines'] = 0
            device['truncated'] = False
            device['filters_applied'] = filters
            device['summary'] = _empty_summary()
            return device

        # 如果指定了包名，获取应用的PID
        resolved_pid = pid
        if package_name and not pid:
            app_pid = hdc.get_app_pid(device, package_name)
            if app_pid:
                resolved_pid = app_pid
                logger.info(f"通过包名 {package_name} 解析到 PID: {app_pid}")
            else:
                return {
                    'success': False,
                    'device_id': device,
                    'error': f'应用 {package_name} 未运行或未找到进程',
                    'hint': '请确保应用已启动',
                    'error_code': 'APP_NOT_RUNNING',
                    'logs': [],
                    'total_lines': 0,
                    'truncated': False,
                    'filters_applied': filters,
                    'summary': _empty_summary()
                }

        # 限制最大行数
        lines = min(lines, LogSecurityConfig.MAX_LOG_LINES)

        # 获取日志（获取更多行以便过滤后仍有足够数据）
        fetch_lines = min(lines * 5, LogSecurityConfig.MAX_LOG_LINES)
        log_text = hdc.get_realtime_logs(device, lines=fetch_lines, tag=tag, pid=resolved_pid)

        if not log_text:
            return {
                'success': True,
                'device_id': device,
                'logs': [],
                'total_lines': 0,
                'truncated': False,
                'filters_applied': filters,
                'summary': _empty_summary(),
                'message': '未获取到日志'
            }

        # 解析日志
        raw_lines = log_text.split('\n')
        entries = LogParser.parse_logs(raw_lines)

        # 构建时间范围
        time_range = _build_time_range(seconds, start_time, end_time)
        filters['time_range'] = time_range

        # 应用过滤
        filtered_entries = LogParser.filter_entries(
            entries,
            level=level,
            tag=tag,
            keyword=keyword,
            time_range=time_range,
            pid=pid,
            seconds=seconds
        )

        # 限制返回行数
        truncated = len(filtered_entries) > lines
        filtered_entries = filtered_entries[:lines]

        # 获取统计
        summary = LogParser.analyze_summary(filtered_entries)

        return {
            'success': True,
            'device_id': device,
            'logs': [e.raw_line for e in filtered_entries],
            'total_lines': len(filtered_entries),
            'truncated': truncated,
            'filters_applied': filters,
            'summary': {
                'level_stats': summary.get('level_stats', {}),
                'time_range': summary.get('time_range')
            }
        }

    except Exception as e:
        error_result = ToolBase.wrap_error(e, 'LOG_FETCH_ERROR')
        error_result['logs'] = []
        error_result['total_lines'] = 0
        error_result['truncated'] = False
        error_result['filters_applied'] = filters
        error_result['summary'] = _empty_summary()
        return error_result


def _build_time_range(seconds: int, start_time: str, end_time: str) -> Optional[dict]:
    """构建时间范围过滤条件"""
    if seconds:
        now = datetime.now()
        return {
            'start': (now - timedelta(seconds=seconds)).isoformat(),
            'end': now.isoformat()
        }
    elif start_time or end_time:
        time_range = {}
        today = datetime.now().strftime('%Y-%m-%d')

        if start_time:
            if len(start_time) <= 8:  # HH:MM:SS
                start_time = f"{today} {start_time}"
            time_range['start'] = start_time

        if end_time:
            if len(end_time) <= 8:
                end_time = f"{today} {end_time}"
            time_range['end'] = end_time

        return time_range
    return None


def logs_fetch(
    device_id: str = None,
    lines: int = 100,
    level: str = None,
    tag: str = None,
    keyword: str = None,
    pid: int = None,
    package_name: str = None,
    start_time: str = None,
    end_time: str = None,
    seconds: int = None
) -> LogsFetchResult:
    """
    从设备获取日志（支持多种过滤条件）

    Args:
        device_id: 设备ID，如果为None则使用第一个设备
        lines: 最大返回行数（默认100，最大50000）
        level: 日志级别过滤 (D/I/W/E/F)，会返回该级别及以上
        tag: Tag 过滤（模糊匹配）
        keyword: 关键字过滤（在日志内容中搜索）
        pid: 进程ID过滤
        package_name: 应用包名过滤（如 com.example.myapplication），自动获取应用PID
        start_time: 开始时间（格式：HH:MM:SS 或 YYYY-MM-DD HH:MM:SS）
        end_time: 结束时间（格式：HH:MM:SS 或 YYYY-MM-DD HH:MM:SS）
        seconds: 获取最近N秒内的日志（与start_time/end_time互斥）

    Returns:
        包含日志内容、过滤信息和统计的字典
    """
    return _logs_fetch_impl(
        device_id=device_id,
        lines=lines,
        level=level,
        tag=tag,
        keyword=keyword,
        pid=pid,
        package_name=package_name,
        start_time=start_time,
        end_time=end_time,
        seconds=seconds
    )


def logs_save_snapshot(
    device_id: str = None,
    output_path: str = None,
    lines: int = 1000,
    level: str = None,
    tag: str = None,
    keyword: str = None,
    package_name: str = None,
    seconds: int = None,
    start_time: str = None,
    end_time: str = None,
    include_analysis: bool = True
) -> LogsSaveResult:
    """
    保存日志快照到本地文件（用于审计和复现）

    Args:
        device_id: 设备ID，如果为None则使用第一个设备
        output_path: 输出文件路径（默认自动生成，保存在 ./hm_logs/ 目录）
        lines: 最大保存行数（默认1000）
        level: 日志级别过滤
        tag: Tag 过滤
        keyword: 关键字过滤
        package_name: 应用包名过滤（如 com.example.myapplication），自动获取应用PID
        seconds: 获取最近N秒内的日志
        start_time: 开始时间
        end_time: 结束时间
        include_analysis: 是否在文件中包含分析摘要

    Returns:
        保存结果，包含文件路径和统计信息
    """
    # 默认值，用于错误返回
    default_result = {
        'saved_path': '',
        'file_size': 0,
        'file_size_human': '0 B',
        'log_count': 0,
        'truncated': False
    }
    
    try:
        # 先获取日志
        fetch_result = _logs_fetch_impl(
            device_id=device_id,
            lines=lines,
            level=level,
            tag=tag,
            keyword=keyword,
            package_name=package_name,
            seconds=seconds,
            start_time=start_time,
            end_time=end_time
        )

        if not fetch_result['success']:
            # 移除 LogsFetchResult 特有的字段（LogsSaveResult 不需要）
            fetch_result.pop('filters_applied', None)
            fetch_result.pop('summary', None)
            fetch_result.pop('logs', None)
            fetch_result.pop('total_lines', None)
            fetch_result.update(default_result)
            return fetch_result

        logs = fetch_result.get('logs', [])
        if not logs:
            return {
                'success': False,
                'device_id': fetch_result.get('device_id', ''),
                'error': '没有日志可保存',
                'error_code': 'NO_LOGS',
                **default_result
            }

        # 确定输出路径
        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"./hm_logs/hilog_snapshot_{timestamp}.txt"

        # 验证路径白名单
        valid, result_path = LogSecurityConfig.validate_save_path(output_path)
        if not valid:
            return {
                'success': False,
                'device_id': fetch_result.get('device_id', ''),
                'error': result_path,
                'error_code': 'PATH_NOT_ALLOWED',
                **default_result
            }

        # 确保目录存在
        output_dir = os.path.dirname(result_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # 写入文件
        _write_log_file(result_path, fetch_result, logs, include_analysis)

        # 获取文件大小
        file_size = os.path.getsize(result_path)

        return {
            'success': True,
            'saved_path': result_path,
            'file_size': file_size,
            'file_size_human': _format_file_size(file_size),
            'log_count': len(logs),
            'device_id': fetch_result.get('device_id'),
            'truncated': fetch_result.get('truncated', False)
        }

    except Exception as e:
        error_result = ToolBase.wrap_error(e, 'LOG_SAVE_ERROR')
        error_result.update(default_result)
        return error_result


def _write_log_file(path: str, fetch_result: dict, logs: List[str], include_analysis: bool):
    """写入日志文件"""
    with open(path, 'w', encoding='utf-8') as f:
        # 写入头部信息
        f.write("=" * 80 + "\n")
        f.write(f"HarmonyOS 日志快照\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"设备ID: {fetch_result.get('device_id', 'N/A')}\n")
        f.write(f"日志行数: {len(logs)}\n")

        # 写入过滤条件
        filters = fetch_result.get('filters_applied', {})
        active_filters = {k: v for k, v in filters.items() if v}
        if active_filters:
            f.write(f"过滤条件: {active_filters}\n")

        f.write("=" * 80 + "\n\n")

        # 写入分析摘要
        if include_analysis:
            summary = fetch_result.get('summary', {})
            if summary:
                f.write("--- 日志分析摘要 ---\n")
                level_stats = summary.get('level_stats', {})
                if level_stats:
                    f.write(f"级别统计: {level_stats}\n")
                time_range = summary.get('time_range')
                if time_range:
                    f.write(f"时间范围: {time_range.get('start', 'N/A')} ~ {time_range.get('end', 'N/A')}\n")
                f.write("\n")

        f.write("--- 日志内容 ---\n\n")

        # 写入日志内容
        for line in logs:
            f.write(line + "\n")


def _format_file_size(size: int) -> str:
    """格式化文件大小"""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size / 1024 / 1024:.1f} MB"


def logs_analyze(
    logs: list = None,
    device_id: str = None,
    package_name: str = None,
    analysis_type: str = "summary",
    level: str = None,
    tag: str = None,
    keyword: str = None,
    lines: int = 1000,
    custom_regex: str = None
) -> LogsAnalyzeResult:
    """
    对日志进行结构化分析（基于正则匹配，不依赖LLM）

    可以直接传入日志列表，或从设备获取日志后分析。

    Args:
        logs: 日志行列表（如果提供则直接分析，否则从设备获取）
        device_id: 设备ID（当 logs 为空时使用）
        package_name: 应用包名过滤（如 com.example.myapplication）
        analysis_type: 分析类型
            - summary: 摘要统计（级别分布、Top Tags、时间范围）
            - errors: 错误分析（E/F级别日志分组、异常类型识别）
            - performance: 性能分析（提取耗时数据、统计指标）
            - crashes: 崩溃分析（Crash/ANR/Exception 识别）
            - keywords: 关键词提取（提取错误码、组件名、异常名、报错短语）
            - custom: 自定义正则匹配
        level: 日志级别过滤 (D/I/W/E/F)
        tag: Tag 过滤
        keyword: 关键字过滤
        lines: 获取日志行数（当从设备获取时）
        custom_regex: 自定义正则表达式（仅 analysis_type=custom 时使用）

    Returns:
        分析结果，包含 success、analysis_type、result 和 evidence_lines
    """
    # 构建过滤配置
    filters = {
        'level': level,
        'tag': tag,
        'keyword': keyword,
        'package_name': package_name
    }
    
    # 默认值，用于错误返回
    default_result = {
        'analysis_type': analysis_type,
        'result': {},
        'evidence_lines': [],
        'total_entries_analyzed': 0,
        'filters_applied': filters
    }
    
    try:
        # 如果没有提供日志，则从设备获取
        if not logs:
            fetch_result = _logs_fetch_impl(
                device_id=device_id,
                package_name=package_name,
                lines=lines,
                tag=tag
            )

            if not fetch_result['success']:
                # 移除 LogsFetchResult 特有的字段（LogsAnalyzeResult 不需要）
                fetch_result.pop('logs', None)
                fetch_result.pop('total_lines', None)
                fetch_result.pop('truncated', None)
                fetch_result.pop('summary', None)
                # filters_applied 会被 default_result 覆盖
                fetch_result.update(default_result)
                return fetch_result

            logs = fetch_result.get('logs', [])
            device_id = fetch_result.get('device_id')

        # 解析日志
        entries = LogParser.parse_logs(logs)

        # 应用过滤
        if level or tag or keyword:
            entries = LogParser.filter_entries(
                entries,
                level=level,
                tag=tag,
                keyword=keyword
            )

        # 执行分析
        result = LogParser.analyze(entries, analysis_type, custom_regex)

        # 获取证据行（用于审计）
        evidence_lines = _extract_evidence_lines(entries, analysis_type)

        return {
            'success': True,
            'analysis_type': analysis_type,
            'result': result,
            'evidence_lines': evidence_lines,
            'total_entries_analyzed': len(entries),
            'device_id': device_id,
            'filters_applied': filters
        }

    except Exception as e:
        error_result = ToolBase.wrap_error(e, 'LOG_ANALYZE_ERROR')
        error_result.update(default_result)
        return error_result


def _extract_evidence_lines(entries: List[LogEntry], analysis_type: str) -> List[str]:
    """提取证据行"""
    evidence_lines = []

    if analysis_type == 'errors':
        error_entries = [e for e in entries if e.level in ('E', 'F')][:10]
        evidence_lines = [e.raw_line for e in error_entries]
    elif analysis_type == 'crashes':
        for e in entries[:100]:
            if any(p.search(e.raw_line) for p in LogParser.ERROR_PATTERNS.values()):
                evidence_lines.append(e.raw_line)
                if len(evidence_lines) >= 10:
                    break
    elif analysis_type == 'keywords':
        error_entries = [e for e in entries if e.level in ('E', 'F', 'W')][:10]
        evidence_lines = [e.raw_line for e in error_entries]

    return evidence_lines
