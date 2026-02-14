"""
日志配置模块

使用 loguru 的 enqueue=True 实现异步日志写入，
避免 I/O 操作阻塞主事件循环（尤其在高频 hdc 命令场景下）。

特性：
- 异步日志写入
- 自动轮转（按大小和时间）
- 自动压缩和清理
- 日志目录大小限制
"""
import sys
import os
import glob
from pathlib import Path
from datetime import datetime, timedelta
from loguru import logger

from ..config import Config

# 项目根目录: harmonyos-mcp-server/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LOG_DIR = _PROJECT_ROOT / "logs"

# 日志配置常量
LOG_ROTATION_SIZE = "100 MB"      # 单文件轮转大小
LOG_ROTATION_TIME = "1 day"       # 按时间轮转
LOG_RETENTION = "7 days"          # 保留天数
LOG_COMPRESSION = "gz"            # 压缩格式
LOG_MAX_DIR_SIZE_MB = 500         # 日志目录最大大小（MB）


def setup_logger():
    """
    配置日志系统

    关键特性：
    - enqueue=True: 日志写入在独立线程中异步执行，不阻塞主线程
    - 控制台输出 + 文件轮转输出双通道
    - 日志路径锚定到项目根目录，不依赖 CWD
    - 自动压缩旧日志文件
    """
    # 确保日志目录存在
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # 移除默认处理器
    logger.remove()

    # 添加控制台输出（异步）
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=Config.LOG_LEVEL,
        colorize=True,
        enqueue=True,
    )

    # 添加文件输出（异步，带轮转和压缩）
    logger.add(
        str(_LOG_DIR / "harmonyos_mcp_{time}.log"),
        rotation=LOG_ROTATION_SIZE,
        retention=LOG_RETENTION,
        compression=LOG_COMPRESSION,
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        enqueue=True,
    )

    # 启动时执行一次清理
    cleanup_old_logs()

    return logger


def cleanup_old_logs(max_age_days: int = 7, max_dir_size_mb: int = None):
    """
    清理旧日志文件
    
    Args:
        max_age_days: 最大保留天数，超过此天数的日志将被删除
        max_dir_size_mb: 日志目录最大大小（MB），超过时删除最旧的文件
    
    Returns:
        删除的文件数量
    """
    max_dir_size_mb = max_dir_size_mb or LOG_MAX_DIR_SIZE_MB
    deleted_count = 0
    
    if not _LOG_DIR.exists():
        return 0
    
    # 1. 按时间删除过期日志
    cutoff_time = datetime.now() - timedelta(days=max_age_days)
    
    for log_file in _LOG_DIR.glob("*.log*"):
        try:
            file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if file_mtime < cutoff_time:
                log_file.unlink()
                deleted_count += 1
                logger.debug(f"删除过期日志: {log_file.name}")
        except Exception as e:
            logger.warning(f"删除日志文件失败: {log_file}, 错误: {e}")
    
    # 2. 按目录大小限制删除最旧的文件
    dir_size_mb = get_log_dir_size_mb()
    if dir_size_mb > max_dir_size_mb:
        # 获取所有日志文件，按修改时间排序（最旧的在前）
        log_files = sorted(
            _LOG_DIR.glob("*.log*"),
            key=lambda f: f.stat().st_mtime
        )
        
        for log_file in log_files:
            if dir_size_mb <= max_dir_size_mb:
                break
            try:
                file_size_mb = log_file.stat().st_size / (1024 * 1024)
                log_file.unlink()
                dir_size_mb -= file_size_mb
                deleted_count += 1
                logger.debug(f"删除日志（空间限制）: {log_file.name}")
            except Exception as e:
                logger.warning(f"删除日志文件失败: {log_file}, 错误: {e}")
    
    if deleted_count > 0:
        logger.info(f"清理了 {deleted_count} 个旧日志文件")
    
    return deleted_count


def get_log_dir_size_mb() -> float:
    """
    获取日志目录大小（MB）
    
    Returns:
        目录大小（MB）
    """
    if not _LOG_DIR.exists():
        return 0.0
    
    total_size = sum(
        f.stat().st_size for f in _LOG_DIR.glob("*") if f.is_file()
    )
    return total_size / (1024 * 1024)


def get_log_stats() -> dict:
    """
    获取日志统计信息
    
    Returns:
        包含日志统计的字典
    """
    if not _LOG_DIR.exists():
        return {
            'log_dir': str(_LOG_DIR),
            'exists': False,
            'file_count': 0,
            'total_size_mb': 0,
            'oldest_file': None,
            'newest_file': None,
        }
    
    log_files = list(_LOG_DIR.glob("*.log*"))
    
    if not log_files:
        return {
            'log_dir': str(_LOG_DIR),
            'exists': True,
            'file_count': 0,
            'total_size_mb': 0,
            'oldest_file': None,
            'newest_file': None,
        }
    
    log_files_sorted = sorted(log_files, key=lambda f: f.stat().st_mtime)
    
    return {
        'log_dir': str(_LOG_DIR),
        'exists': True,
        'file_count': len(log_files),
        'total_size_mb': round(get_log_dir_size_mb(), 2),
        'oldest_file': log_files_sorted[0].name if log_files_sorted else None,
        'newest_file': log_files_sorted[-1].name if log_files_sorted else None,
        'max_size_mb': LOG_MAX_DIR_SIZE_MB,
        'retention_days': int(LOG_RETENTION.split()[0]),
    }

