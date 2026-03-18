"""
日志配置模块

委托给 common 的参数化 logger，
使用 harmonyos_mcp 专属的应用名和配置。
"""
from common.utils.logger import (
    setup_logger as _setup_logger
)
from ..config import Config


def setup_logger():
    """配置 harmonyos_mcp 的日志系统"""
    return _setup_logger(app_name="harmonyos_mcp", log_level=Config.LOG_LEVEL)
