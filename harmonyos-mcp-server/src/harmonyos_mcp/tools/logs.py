"""
日志分析工具

提供 hilog 文件获取、日志获取、保存快照、结构化分析等功能。
"""
import asyncio
import os
import zipfile
from datetime import datetime, timedelta
from typing import Optional, List
from loguru import logger

from ..container import get_hdc, get_hilogtool
from ..config import LogSecurityConfig
from ..utils.log_parser import LogParser, LogEntry
from ..types import LogsFetchResult, LogsSaveResult, LogsAnalyzeResult, AnalysisType, HilogReceiveResult
from .base import ToolBase
from .registry import mcp_tool


@mcp_tool(category="logs")
@ToolBase.handle_tool_error('HILOG_RECEIVE_ERROR', files=[], total_size=0)
@ToolBase.with_device(files=[], total_size=0)
@ToolBase.validate_params(local_dir=['path'])
async def hilog_receive(device_id: Optional[str] = None, local_dir: Optional[str] = None) -> HilogReceiveResult:
    """
    从HarmonyOS设备的 /data/log/hilog 目录中获取所有 hilog 日志文件和 dict 解密文件

    Args:
        device_id: 设备ID，如果为None则使用第一个设备
        local_dir: 本地保存目录，如果为None则使用当前工作目录

    Returns:
        包含获取结果、文件列表和统计信息的字典
    """
    hdc = get_hdc()
    result = await asyncio.to_thread(hdc.hilog_receive, device_id, local_dir)
    
    # 添加设备ID到结果
    result['device_id'] = device_id
    
    # 确保必需字段存在
    if 'files' not in result:
        result['files'] = []
    if 'total_size' not in result:
        result['total_size'] = 0
    
    return result


def _empty_filters() -> dict:
    """返回空的过滤配置"""
    return {}


def _empty_summary() -> dict:
    """返回空的摘要"""
    return {
        'level_stats': {}
    }


def _clean_dict(d: dict) -> dict:
    """移除字典中值为 None 的键，避免 MCP schema 校验失败"""
    return {k: v for k, v in d.items() if v is not None}


def _expand_short_time(t: str) -> str:
    """
    将 HH:MM:SS 短格式时间扩展为完整的 YYYY-MM-DD HH:MM:SS。
    
    处理跨午夜场景：如果扩展后的时间在未来超过1小时，
    说明用户意图是昨天的时间，自动回退一天。
    
    Args:
        t: 时间字符串，可能是 HH:MM:SS 或 YYYY-MM-DD HH:MM:SS
        
    Returns:
        完整的时间字符串
    """
    if len(t) > 8:
        return t
    today = datetime.now()
    candidate = f"{today.strftime('%Y-%m-%d')} {t}"
    try:
        dt = datetime.fromisoformat(candidate)
        # 如果结果超过现在1小时以上，说明跨午夜了，回退到昨天
        if dt > today + timedelta(hours=1):
            yesterday = today - timedelta(days=1)
            candidate = f"{yesterday.strftime('%Y-%m-%d')} {t}"
    except ValueError:
        pass
    return candidate


def _needs_historical_logs(start_time: str, seconds: int) -> bool:
    """
    判断是否需要从历史落盘文件读取日志
    
    规则: 如果请求时间范围超过10分钟之前，则需要历史文件
    """
    if seconds and seconds > 600:
        return True
    
    if start_time:
        st = _expand_short_time(start_time)
        try:
            start_dt = datetime.fromisoformat(st)
            cutoff = datetime.now() - timedelta(minutes=10)
            return start_dt < cutoff
        except ValueError:
            pass
    
    return False


def _pull_dict_files(hdc, device: str, local_dir: str) -> Optional[str]:
    """
    从设备拉取 hilog dict 解密文件（带权限绕过）
    
    策略: 先 cp 到 /data/local/tmp 再 pull（绕过 /data/log/hilog 权限限制）
    
    Returns:
        解压后的 dict 目录路径，失败返回 None
    """
    # 1. 列出 dict 文件
    list_result = hdc.execute_shell(device, "ls /data/log/hilog/hilog_dict.*.zip 2>/dev/null")
    if not list_result['success'] or not list_result['stdout'].strip():
        logger.info("未找到 hilog dict 文件")
        return None
    
    dict_files = [f.strip() for f in list_result['stdout'].split('\n') if f.strip() and 'hilog_dict' in f]
    if not dict_files:
        return None
    
    # 2. 复制到设备临时目录后拉取
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
        # 清理设备临时目录
        hdc.execute_shell(device, f"rm -rf {tmp_dir}")
    
    if not pulled_dicts:
        return None
    
    # 3. 解压最新的 dict zip 文件
    dict_extract_dir = os.path.join(local_dir, "dict_extracted")
    os.makedirs(dict_extract_dir, exist_ok=True)
    
    try:
        with zipfile.ZipFile(pulled_dicts[0], 'r') as zip_ref:
            zip_ref.extractall(dict_extract_dir)
        logger.info(f"dict 文件解压到: {dict_extract_dir}")
        return dict_extract_dir
    except Exception as e:
        logger.error(f"dict 文件解压失败: {e}")
        return None


def _fetch_from_historical_files(
    device: str,
    lines: int,
    level: str,
    tag: str,
    keyword: str,
    start_time: str,
    end_time: str,
    package_name: str
) -> dict:
    """
    从设备历史 hilog 落盘文件中获取日志
    
    流程: list_hilog_files -> pull_hilog_files -> hilogtool 解密 -> 解析过滤
    """
    hdc = get_hdc()
    hilogtool = get_hilogtool()
    
    # 1. 检查 hilogtool 是否可用
    if not hilogtool.is_available():
        return {
            'success': False,
            'error': 'hilogtool 不可用，无法读取历史日志文件',
            'hint': '请设置 HILOGTOOL_PATH 环境变量指向 hilogtool.exe 路径',
            'error_code': 'HILOGTOOL_NOT_AVAILABLE',
            'logs': [],
            'total_lines': 0,
            'truncated': False,
            'source': 'persist_file',
            'dict_used': False,
            'files_count': 0,
            'summary': _empty_summary()
        }
    
    # 2. 列出设备上的 hilog 文件
    list_result = hdc.list_hilog_files(device)
    if not list_result['success'] or not list_result.get('files'):
        return {
            'success': False,
            'device_id': device,
            'error': '未找到历史日志文件',
            'error_code': 'NO_HISTORICAL_FILES',
            'logs': [],
            'total_lines': 0,
            'truncated': False,
            'source': 'persist_file',
            'dict_used': False,
            'files_count': 0,
            'summary': _empty_summary()
        }
    
    # 3. 解析时间范围为 datetime
    start_dt = None
    end_dt = None
    
    if start_time:
        st = _expand_short_time(start_time)
        try:
            start_dt = datetime.fromisoformat(st)
        except ValueError:
            pass
    
    if end_time:
        et = _expand_short_time(end_time)
        try:
            end_dt = datetime.fromisoformat(et)
        except ValueError:
            pass
    
    # 4. 创建本地目录
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    local_dir = os.path.abspath(f"./hilog_files/fetch_{timestamp}")
    os.makedirs(local_dir, exist_ok=True)
    
    # 5. 先按时间范围过滤文件列表，再按与目标时间的距离排序，最后限制数量
    all_files = [
        f for f in list_result['files']
        if not f['name'].startswith('hilog_diag.')
        and not f['name'].startswith('hilog_dict.')
        and not f['name'].startswith('hilog_kmsg.')
    ]
    if start_dt or end_dt:
        matched_files = []
        buffer = timedelta(hours=1)
        for f in all_files:
            fts = f.get('timestamp_dt')
            if not fts:
                matched_files.append(f)
                continue
            if start_dt and fts < (start_dt - buffer):
                continue
            if end_dt and fts > (end_dt + buffer):
                continue
            matched_files.append(f)
        target_center = start_dt
        if start_dt and end_dt:
            target_center = start_dt + (end_dt - start_dt) / 2
        elif end_dt:
            target_center = end_dt
        max_distance = timedelta(days=36500)
        matched_files.sort(key=lambda f: abs(f['timestamp_dt'] - target_center) if f.get('timestamp_dt') else max_distance)
        files_to_pull = matched_files[:5]
    else:
        files_to_pull = all_files[:5]
    
    if not files_to_pull:
        return {
            'success': False,
            'device_id': device,
            'error': f'未找到时间范围 {start_time} ~ {end_time} 内的历史日志文件',
            'error_code': 'NO_MATCHING_FILES',
            'logs': [],
            'total_lines': 0,
            'truncated': False,
            'source': 'persist_file',
            'dict_used': False,
            'files_count': 0,
            'summary': _empty_summary()
        }
    
    logger.info(f"匹配到 {len(files_to_pull)} 个历史日志文件: {[f['name'] for f in files_to_pull]}")
    
    # 6. 拉取文件
    pull_result = hdc.pull_hilog_files(
        device,
        files_to_pull,
        local_dir
    )
    
    if not pull_result['success'] or not pull_result.get('pulled_files'):
        return {
            'success': False,
            'device_id': device,
            'error': f'拉取历史日志文件失败 (匹配 {len(files_to_pull)} 个文件)',
            'error_code': 'PULL_FILES_FAILED',
            'logs': [],
            'total_lines': 0,
            'truncated': False,
            'source': 'persist_file',
            'dict_used': False,
            'files_count': 0,
            'summary': _empty_summary()
        }
    
    # 7. 拉取 dict 解密文件
    dict_path = _pull_dict_files(hdc, device, local_dir)
    
    # 8. 逐个文件解密并合并日志
    all_logs = []
    dict_used = False
    max_lines = min(lines * 5, LogSecurityConfig.MAX_LOG_LINES)
    
    for file_info in pull_result['pulled_files']:
        local_path = file_info['local_path']
        logger.info(f"解析历史日志文件: {local_path}")
        
        parse_result = hilogtool.parse_and_read(
            local_path,
            dict_path=dict_path,
            max_lines=max_lines - len(all_logs)
        )
        
        if parse_result['success']:
            logs = parse_result.get('logs', [])
            
            for line in logs[:10]:
                if 'OpenUuidFile fail' in line:
                    logger.warning("hilogtool 输出包含 OpenUuidFile fail 错误，dict 文件可能无效")
                    break
            
            all_logs.extend(logs)
            if parse_result.get('dict_used'):
                dict_used = True
        else:
            logger.warning(f"解析文件失败: {local_path}, 错误: {parse_result.get('error')}")
        
        if len(all_logs) >= max_lines:
            break
    
    if not all_logs:
        return {
            'success': False,
            'device_id': device,
            'error': '历史日志文件解析后无内容',
            'error_code': 'PARSE_EMPTY',
            'logs': [],
            'total_lines': 0,
            'truncated': False,
            'source': 'persist_file',
            'dict_used': dict_used,
            'files_count': len(pull_result['pulled_files']),
            'summary': _empty_summary()
        }
    
    # 8. 解析为结构化日志条目
    entries = LogParser.parse_logs(all_logs)
    
    # 9. 构建时间范围并应用过滤
    time_range = _build_time_range(None, start_time, end_time)
    
    filtered_entries = LogParser.filter_entries(
        entries,
        level=level,
        tag=tag,
        keyword=keyword,
        time_range=time_range
    )
    
    # package_name 作为关键字过滤（不依赖 PID）
    if package_name:
        pkg_lower = package_name.lower()
        filtered_entries = [e for e in filtered_entries if pkg_lower in e.raw_line.lower()]
    
    # 10. 限制返回行数
    lines = min(lines, LogSecurityConfig.MAX_LOG_LINES)
    truncated = len(filtered_entries) > lines
    filtered_entries = filtered_entries[:lines]
    
    # 11. 获取统计
    summary = LogParser.analyze_summary(filtered_entries)
    
    return {
        'success': True,
        'device_id': device,
        'logs': [e.raw_line for e in filtered_entries],
        'total_lines': len(filtered_entries),
        'truncated': truncated,
        'source': 'persist_file',
        'dict_used': dict_used,
        'files_count': len(pull_result['pulled_files']),
        'summary': _clean_dict({
            'level_stats': summary.get('level_stats', {}),
            'time_range': summary.get('time_range')
        })
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
    日志获取的内部实现（同步，供 asyncio.to_thread 调用）

    Args:
        package_name: 应用包名，如果指定则自动获取该应用的PID进行过滤
    """
    # 归一化 level 参数：支持 'Error'->'E', 'Warning'->'W' 等写法
    level = LogParser.normalize_level(level) or level

    # 构建过滤配置（用于所有返回路径）
    filters = _clean_dict({
        'level': level,
        'tag': tag,
        'keyword': keyword,
        'pid': pid,
        'time_range': None,
        'seconds': seconds
    })
    
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
            device['source'] = 'realtime_buffer'
            device['dict_used'] = False
            device['files_count'] = 0
            return device

        # === 历史日志回退: 当请求时间超过10分钟前，从落盘文件获取 ===
        if _needs_historical_logs(start_time, seconds):
            logger.info("检测到历史时间范围，切换到历史文件读取模式")
            result = _fetch_from_historical_files(
                device=device,
                lines=lines,
                level=level,
                tag=tag,
                keyword=keyword,
                start_time=start_time,
                end_time=end_time,
                package_name=package_name
            )
            result['filters_applied'] = _clean_dict(filters)
            return result

        # === 实时缓冲区路径 ===

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
                    'summary': _empty_summary(),
                    'source': 'realtime_buffer',
                    'dict_used': False,
                    'files_count': 0
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
                'source': 'realtime_buffer',
                'dict_used': False,
                'files_count': 0,
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
            'source': 'realtime_buffer',
            'dict_used': False,
            'files_count': 0,
            'filters_applied': _clean_dict(filters),
            'summary': _clean_dict({
                'level_stats': summary.get('level_stats', {}),
                'time_range': summary.get('time_range')
            })
        }

    except Exception as e:
        error_result = ToolBase.wrap_error(e, 'LOG_FETCH_ERROR')
        error_result['logs'] = []
        error_result['total_lines'] = 0
        error_result['truncated'] = False
        error_result['filters_applied'] = filters
        error_result['summary'] = _empty_summary()
        error_result['source'] = 'realtime_buffer'
        error_result['dict_used'] = False
        error_result['files_count'] = 0
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

        if start_time:
            time_range['start'] = _expand_short_time(start_time)

        if end_time:
            time_range['end'] = _expand_short_time(end_time)

        return time_range
    return None


@mcp_tool(category="logs")
async def logs_fetch(
    device_id: Optional[str] = None,
    lines: int = 100,
    level: Optional[str] = None,
    tag: Optional[str] = None,
    keyword: Optional[str] = None,
    pid: Optional[int] = None,
    package_name: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    seconds: Optional[int] = None
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
    return await asyncio.to_thread(
        _logs_fetch_impl,
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


@mcp_tool(category="logs")
async def logs_save_snapshot(
    device_id: Optional[str] = None,
    output_path: Optional[str] = None,
    lines: int = 1000,
    level: Optional[str] = None,
    tag: Optional[str] = None,
    keyword: Optional[str] = None,
    package_name: Optional[str] = None,
    seconds: Optional[int] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
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
    def _save():
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
            _output_path = output_path
            if not _output_path:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                _output_path = f"./hm_logs/hilog_snapshot_{timestamp}.txt"

            # 验证路径白名单
            valid, result_path = LogSecurityConfig.validate_save_path(_output_path)
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

    return await asyncio.to_thread(_save)


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


@mcp_tool(category="logs")
async def logs_analyze(
    logs: Optional[List[str]] = None,
    input_file: Optional[str] = None,
    input_files: Optional[List[str]] = None,
    device_id: Optional[str] = None,
    package_name: Optional[str] = None,
    analysis_type: str = "summary",
    level: Optional[str] = None,
    tag: Optional[str] = None,
    keyword: Optional[str] = None,
    lines: int = 1000,
    custom_regex: Optional[str] = None
) -> LogsAnalyzeResult:
    """
    对日志进行结构化分析（基于正则匹配，不依赖LLM）

    可以直接传入日志列表、指定本地日志文件路径，或从设备获取日志后分析。

    Args:
        logs: 日志行列表（如果提供则直接分析）
        input_file: 本地日志文件路径（单文件）
        input_files: 本地日志文件路径列表（多文件，内容会合并分析）
        device_id: 设备ID（当 logs 和文件均未提供时，从设备获取）
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
    def _analyze():
        # 构建过滤配置
        filters = _clean_dict({
            'level': level,
            'tag': tag,
            'keyword': keyword,
            'package_name': package_name
        })
        
        # 默认值，用于错误返回
        default_result = {
            'analysis_type': analysis_type,
            'result': {},
            'evidence_lines': [],
            'total_entries_analyzed': 0,
            'filters_applied': filters
        }
        
        # 使用可变的本地变量
        _logs = logs
        _device_id = device_id
        
        try:
            # 从文件读取日志（input_file / input_files）
            if not _logs and (input_file or input_files):
                file_paths = []
                if input_files:
                    file_paths.extend(input_files)
                if input_file and input_file not in file_paths:
                    file_paths.append(input_file)

                all_lines = []
                for fpath in file_paths:
                    if not os.path.isfile(fpath):
                        error_result = {
                            'success': False,
                            'error': f'文件不存在: {fpath}',
                            'error_code': 'FILE_NOT_FOUND'
                        }
                        error_result.update(default_result)
                        return error_result
                    try:
                        with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                            all_lines.extend(f.read().splitlines())
                    except OSError as e:
                        error_result = {
                            'success': False,
                            'error': f'读取文件失败: {fpath}: {e}',
                            'error_code': 'FILE_READ_ERROR'
                        }
                        error_result.update(default_result)
                        return error_result
                _logs = all_lines

            # 如果没有提供日志，则从设备获取
            if not _logs:
                fetch_result = _logs_fetch_impl(
                    device_id=_device_id,
                    package_name=package_name,
                    lines=lines,
                    tag=tag
                )

                if not fetch_result['success']:
                    fetch_result.pop('logs', None)
                    fetch_result.pop('total_lines', None)
                    fetch_result.pop('truncated', None)
                    fetch_result.pop('summary', None)
                    fetch_result.update(default_result)
                    return fetch_result

                _logs = fetch_result.get('logs', [])
                _device_id = fetch_result.get('device_id')

            # 解析日志
            entries = LogParser.parse_logs(_logs)

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
                'device_id': _device_id or '',
                'filters_applied': filters
            }

        except Exception as e:
            error_result = ToolBase.wrap_error(e, 'LOG_ANALYZE_ERROR')
            error_result.update(default_result)
            return error_result

    return await asyncio.to_thread(_analyze)


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
