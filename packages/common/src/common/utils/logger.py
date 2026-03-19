"""Shared logger configuration."""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from loguru import logger


def _resolve_log_dir(app_name: str = "harmonyos-dev-mcp") -> Path:
    """Store service logs under LOCALAPPDATA on Windows."""
    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / app_name / "logs"

    return Path.home() / ".local" / "share" / app_name / "logs"


_LOG_DIR = _resolve_log_dir()

LOG_ROTATION_SIZE = "100 MB"
LOG_ROTATION_TIME = "1 day"
LOG_RETENTION = "7 days"
LOG_COMPRESSION = "gz"
LOG_MAX_DIR_SIZE_MB = 500


def setup_logger(app_name: str = "harmonyos_dev_mcp", log_level: str = "INFO"):
    """Configure console and rotating file logging."""
    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger.remove()

    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True,
        enqueue=True,
    )

    logger.add(
        str(_LOG_DIR / f"{app_name}_{{time}}.log"),
        rotation=LOG_ROTATION_SIZE,
        retention=LOG_RETENTION,
        compression=LOG_COMPRESSION,
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        enqueue=True,
    )

    cleanup_old_logs()
    return logger


def cleanup_old_logs(max_age_days: int = 7, max_dir_size_mb: int = None) -> int:
    """Delete expired or oversized log files."""
    max_dir_size_mb = max_dir_size_mb or LOG_MAX_DIR_SIZE_MB
    deleted_count = 0

    if not _LOG_DIR.exists():
        return 0

    cutoff_time = datetime.now() - timedelta(days=max_age_days)
    for log_file in _LOG_DIR.glob("*.log*"):
        try:
            file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if file_mtime < cutoff_time:
                log_file.unlink()
                deleted_count += 1
                logger.debug(f"deleted expired log file: {log_file.name}")
        except Exception as exc:
            logger.warning(f"failed to delete log file {log_file}: {exc}")

    dir_size_mb = get_log_dir_size_mb()
    if dir_size_mb > max_dir_size_mb:
        log_files = sorted(_LOG_DIR.glob("*.log*"), key=lambda path: path.stat().st_mtime)
        for log_file in log_files:
            if dir_size_mb <= max_dir_size_mb:
                break
            try:
                file_size_mb = log_file.stat().st_size / (1024 * 1024)
                log_file.unlink()
                dir_size_mb -= file_size_mb
                deleted_count += 1
                logger.debug(f"deleted log file due to size limit: {log_file.name}")
            except Exception as exc:
                logger.warning(f"failed to delete log file {log_file}: {exc}")

    if deleted_count > 0:
        logger.info(f"deleted {deleted_count} old log files")

    return deleted_count


def get_log_dir_size_mb() -> float:
    """Return the current log directory size in MB."""
    if not _LOG_DIR.exists():
        return 0.0

    total_size = sum(path.stat().st_size for path in _LOG_DIR.glob("*") if path.is_file())
    return total_size / (1024 * 1024)
