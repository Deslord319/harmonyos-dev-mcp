"""
配置管理基类

支持环境变量、懒加载初始化。
"""
import os
from typing import Dict, Any
from loguru import logger


class ConfigBase:
    """配置管理基类"""

    _initialized: bool = False

    LOG_LEVEL: str = "INFO"
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 2
    COMMAND_TIMEOUT: int = 30

    @classmethod
    def ensure_init(cls):
        if not cls._initialized:
            cls.init()

    @classmethod
    def init(cls):
        cls._initialized = True
        cls.LOG_LEVEL = os.getenv("LOG_LEVEL", cls.LOG_LEVEL)
        cls.MAX_RETRIES = int(os.getenv("MAX_RETRIES", str(cls.MAX_RETRIES)))
        cls.RETRY_DELAY = int(os.getenv("RETRY_DELAY", str(cls.RETRY_DELAY)))
        cls.COMMAND_TIMEOUT = int(os.getenv("COMMAND_TIMEOUT", str(cls.COMMAND_TIMEOUT)))
        logger.debug(f"配置初始化完成: {cls.__name__}")

    @classmethod
    def get_config_info(cls) -> Dict[str, Any]:
        return {
            "LOG_LEVEL": cls.LOG_LEVEL,
            "MAX_RETRIES": cls.MAX_RETRIES,
            "RETRY_DELAY": cls.RETRY_DELAY,
            "COMMAND_TIMEOUT": cls.COMMAND_TIMEOUT,
        }
