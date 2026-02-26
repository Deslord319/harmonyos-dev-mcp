"""
日志查询主模块

提供统一的日志查询入口
"""
import os
from datetime import datetime
from typing import Optional, List

from loguru import logger

from ...container import get_hdc
from ...config import LogSecurityConfig
from ...types import LogsQueryResult
from ...tools.base import ToolBase
from ...tools.registry import mcp_tool
from .parser import LogParser, FilterStats
from .time_utils import (
    _parse_time_expr,
    _build_time_range,
    _format_file_size,
    _needs_historical_logs,
)
from .historian import fetch_historical_logs, _check_and_cleanup_cache


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


def _clean_dict(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None}


def _query_impl(
    device_id=None, logs=None, input_file=None, input_files=None,
    lines=100, level=None, tag=None, tag_search=None, keyword=None,
    domain=None, pid=None, package_name=None, start_time=None,
    end_time=None, seconds=None, analysis_type="summary",
    custom_regex=None, save_path=None, time_expr=None,
    include_diagnostics=False,
):
    """logs_query 的同步实现"""
    
    _check_and_cleanup_cache()

    if time_expr and not start_time and not end_time and not seconds:
        parsed = _parse_time_expr(time_expr)
        if parsed:
            start_time = parsed['start'].strftime('%Y-%m-%d %H:%M:%S')
            end_time = parsed['end'].strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"time_expr '{time_expr}' -> {start_time} ~ {end_time}")

    filters = _clean_dict({
        'level': level, 'tag': tag, 'tag_search': tag_search,
        'keyword': keyword, 'domain': domain, 'pid': pid,
        'package_name': package_name, 'seconds': seconds,
        'start_time': start_time, 'end_time': end_time,
    })

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
            MAX_FILE_SIZE = 200 * 1024 * 1024
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
                hist = fetch_historical_logs(device, start_time, end_time, lines)
                if not hist['success']:
                    hist['filters_applied'] = filters
                    return hist
                raw_lines = hist['raw_lines']
                extra['dict_used'] = hist.get('dict_used', False)
                extra['dict_status'] = hist.get('dict_status', 'unavailable')
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
                fetch_n = min(lines * LogSecurityConfig.FETCH_MULTIPLIER, LogSecurityConfig.MAX_LOG_LINES)
                log_text = hdc.get_realtime_logs(device, lines=fetch_n, tag=tag, pid=resolved_pid)
                raw_lines = log_text.split('\n') if log_text else []

        entries = LogParser.parse_logs(raw_lines or [])

        time_range = _build_time_range(seconds, start_time, end_time)
        pkg_filter = package_name if (package_name and source != 'realtime_buffer') else None

        filter_result = LogParser.filter_entries(
            entries, level=level, tag=tag, tag_search=tag_search,
            keyword=keyword, domain=domain, time_range=time_range,
            pid=pid, seconds=seconds, package_name=pkg_filter,
            collect_stats=include_diagnostics,
        )

        if include_diagnostics and isinstance(filter_result, tuple):
            filtered, stats = filter_result
        else:
            filtered = filter_result
            stats = None

        max_n = min(lines, LogSecurityConfig.MAX_LOG_LINES)
        truncated = len(filtered) > max_n
        filtered = filtered[:max_n]

        analysis_result = LogParser.analyze(filtered, analysis_type, custom_regex)

        saved = None
        if save_path is not None:
            saved = _save_logs(save_path, _device_id, filtered, filters, analysis_result)

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

        if include_diagnostics and stats:
            result['diagnostics'] = {
                'total_scanned': stats.total_scanned,
                'parse_success': sum(1 for e in entries if e.level),
                'parse_failed': sum(1 for e in entries if not e.level),
                'filter_stats': {
                    'level_filtered': stats.level_filtered,
                    'tag_filtered': stats.tag_filtered,
                    'tag_search_filtered': stats.tag_search_filtered,
                    'keyword_filtered': stats.keyword_filtered,
                    'domain_filtered': stats.domain_filtered,
                    'pid_filtered': stats.pid_filtered,
                    'time_filtered': stats.time_filtered,
                    'package_filtered': stats.package_filtered,
                    'noise_filtered': stats.noise_filtered,
                    'passed': stats.passed,
                },
            }

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


@mcp_tool(category="general")
async def logs_query(
    device_id: Optional[str] = None,
    logs: Optional[List[str]] = None,
    input_file: Optional[str] = None,
    input_files: Optional[List[str]] = None,
    lines: int = 100,
    level: Optional[str] = None,
    tag: Optional[str] = None,
    tag_search: Optional[str] = None,
    keyword: Optional[str] = None,
    domain: Optional[str] = None,
    pid: Optional[int] = None,
    package_name: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    seconds: Optional[int] = None,
    analysis_type: str = "summary",
    custom_regex: Optional[str] = None,
    save_path: Optional[str] = None,
    time_expr: Optional[str] = None,
    include_diagnostics: bool = False,
) -> LogsQueryResult:
    """
    统一日志查询工具 - 拉取 / 解析 / 过滤 / 分析 / 保存 一体化

    Args:
        device_id: 设备ID，为空时使用第一个设备
        logs: 直接传入日志行列表（优先级最高）
        input_file: 本地日志文件路径
        input_files: 多个本地文件路径
        lines: 最大返回行数（默认100，上限50000）
        level: 日志级别过滤：D/I/W/E/F
        tag: TAG 过滤（匹配解析后的 tag 字段）
        tag_search: TAG 搜索（在原始行中搜索，不依赖解析）
        keyword: 关键字过滤（在原始行中搜索）
        domain: hilog domain 过滤（支持 0x0006 或 C00006 格式）
        pid: 进程 ID 过滤
        package_name: 应用包名过滤
        start_time: 开始时间
        end_time: 结束时间
        seconds: 最近 N 秒
        analysis_type: 分析类型（summary/custom）
        custom_regex: 自定义正则分析
        save_path: 保存路径
        time_expr: 自然语言时间表达式（如"最近10分钟"）
        include_diagnostics: 返回诊断统计信息（默认 False）

    Returns:
        查询结果字典
    """
    import asyncio
    return await asyncio.to_thread(
        _query_impl,
        device_id=device_id, logs=logs, input_file=input_file,
        input_files=input_files, lines=lines, level=level, tag=tag,
        tag_search=tag_search, keyword=keyword, domain=domain, pid=pid,
        package_name=package_name, start_time=start_time, end_time=end_time,
        seconds=seconds, analysis_type=analysis_type, custom_regex=custom_regex,
        save_path=save_path, time_expr=time_expr,
        include_diagnostics=include_diagnostics,
    )
