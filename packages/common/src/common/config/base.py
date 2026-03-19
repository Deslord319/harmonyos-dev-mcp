"""Shared runtime configuration sourced from environment variables."""

import os
from typing import Any

from loguru import logger


class ConfigBase:
    """Base configuration with lazy environment initialization."""

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
    def _get_env_value(cls, key: str, default: Any) -> Any:
        value = os.getenv(key)
        return default if value is None else value

    @classmethod
    def init(cls):
        cls._initialized = True
        cls.LOG_LEVEL = cls._get_env_value("LOG_LEVEL", cls.LOG_LEVEL)
        cls.MAX_RETRIES = int(cls._get_env_value("MAX_RETRIES", str(cls.MAX_RETRIES)))
        cls.RETRY_DELAY = int(cls._get_env_value("RETRY_DELAY", str(cls.RETRY_DELAY)))
        cls.COMMAND_TIMEOUT = int(
            cls._get_env_value("COMMAND_TIMEOUT", str(cls.COMMAND_TIMEOUT))
        )
        logger.debug(f"Initialized config: {cls.__name__}")
