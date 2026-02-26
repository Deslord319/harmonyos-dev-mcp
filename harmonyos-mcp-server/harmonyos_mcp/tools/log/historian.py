"""
历史日志获取模块

提供从设备拉取历史日志文件、解密等功能
"""
import os
import zipfile
from datetime import datetime, timedelta
from typing import Optional, List

from loguru import logger

from ....container import get_hdc, get_hilogtool
from ....config import LogSecurityConfig


def _pull_dict_files(hdc, device: str, local_dir: str) -> Optional[str]:
    """从设备拉取 hilog dict 解密文件"""
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


def _cleanup_old_cache_dirs() -> dict:
    """清理过期的 hilog_files 缓存目录"""
    from pathlib import Path
    import shutil
    
    base_dir = Path("./hilog_files")
    if not base_dir.exists():
        return {'cleaned': 0, 'freed_bytes': 0, 'message': '缓存目录不存在'}
    
    import re
    cutoff = datetime.now() - timedelta(days=LogSecurityConfig.AUTO_CLEANUP_DAYS)
    cleaned_count = 0
    freed_bytes = 0
    
    for subdir in base_dir.iterdir():
        if subdir.is_dir():
            try:
                m = re.search(r'fetch_(\d{8}_\d{6})', subdir.name)
                if m:
                    dir_time = datetime.strptime(m.group(1), '%Y%m%d_%H%M%S')
                    if dir_time < cutoff:
                        dir_size = sum(f.stat().st_size for f in subdir.rglob('*') if f.is_file())
                        shutil.rmtree(subdir)
                        cleaned_count += 1
                        freed_bytes += dir_size
                        logger.info(f"清理过期缓存目录: {subdir}")
            except Exception as e:
                logger.warning(f"清理目录失败 {subdir}: {e}")
    
    return {
        'cleaned': cleaned_count,
        'freed_bytes': freed_bytes,
        'freed_mb': round(freed_bytes / 1024 / 1024, 2),
        'message': f'清理了 {cleaned_count} 个过期目录，释放 {freed_bytes / 1024 / 1024:.2f} MB'
    }


def _check_and_cleanup_cache() -> None:
    """检查缓存目录大小，必要时触发清理"""
    from pathlib import Path
    
    base_dir = Path("./hilog_files")
    if not base_dir.exists():
        return
    
    total_size = sum(f.stat().st_size for f in base_dir.rglob('*') if f.is_file())
    total_mb = total_size / 1024 / 1024
    
    if total_mb > LogSecurityConfig.MAX_CACHE_SIZE_MB:
        logger.warning(f"缓存目录大小 {total_mb:.1f}MB 超过限制 {LogSecurityConfig.MAX_CACHE_SIZE_MB}MB，触发清理")
        result = _cleanup_old_cache_dirs()
        logger.info(result['message'])


def fetch_historical_logs(device, start_time, end_time, max_lines) -> dict:
    """从历史 hilog 落盘文件获取原始日志行"""
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

    start_dt = end_dt = None
    if start_time:
        from .time_utils import _expand_short_time
        try:
            start_dt = datetime.fromisoformat(_expand_short_time(start_time))
        except ValueError:
            pass
    if end_time:
        from .time_utils import _expand_short_time
        try:
            end_dt = datetime.fromisoformat(_expand_short_time(end_time))
        except ValueError:
            pass

    local_dir = os.path.abspath(
        f"./hilog_files/fetch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    os.makedirs(local_dir, exist_ok=True)

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

    dict_path = _pull_dict_files(hdc, device, local_dir)
    all_logs: List[str] = []
    dict_used = False
    dict_status = 'unavailable'
    cap = min(max_lines * LogSecurityConfig.FETCH_MULTIPLIER, LogSecurityConfig.MAX_LOG_LINES)

    for fi in pull_result['pulled_files']:
        local_path = fi['local_path']
        logger.info(f"解析历史日志文件: {local_path}")
        pr = hilogtool.parse_and_read(local_path, dict_path=dict_path, max_lines=cap - len(all_logs))
        if pr['success']:
            logs = pr.get('logs', [])
            for line in logs[:10]:
                if 'OpenUuidFile fail' in line or 'decrypt fail' in line:
                    dict_status = 'decrypt_failed'
                    logger.warning("hilogtool 输出包含解密失败错误，dict 文件可能无效")
                    break
            all_logs.extend(logs)
            if pr.get('dict_used'):
                dict_used = True
                dict_status = 'success'
        else:
            logger.warning(f"解析文件失败: {local_path}, 错误: {pr.get('error')}")
        if len(all_logs) >= cap:
            break

    if not all_logs:
        return {
            'success': False, 'device_id': device,
            'error': '历史日志文件解析后无内容', 'error_code': 'PARSE_EMPTY',
            'logs': [], 'total_lines': 0, 'truncated': False,
            'dict_used': dict_used, 'dict_status': dict_status, 'files_count': len(pull_result['pulled_files']),
        }

    return {
        'success': True,
        'raw_lines': all_logs,
        'dict_used': dict_used,
        'dict_status': dict_status,
        'files_count': len(pull_result['pulled_files']),
        'device_id': device,
    }
