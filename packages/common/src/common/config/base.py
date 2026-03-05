"""
配置管理基类

支持环境变量、配置文件（YAML/JSON）、懒加载初始化。
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, Union
from loguru import logger

try:
    import yaml
except ImportError:
    yaml = None


class ConfigBase:
    """配置管理基类"""

    _initialized: bool = False
    _config_file: Optional[str] = None

    LOG_LEVEL: str = "INFO"
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 2
    COMMAND_TIMEOUT: int = 30

    @classmethod
    def ensure_init(cls):
        if not cls._initialized:
            cls.init()

    @classmethod
    def set_config_file(cls, config_path: str):
        """设置配置文件路径"""
        cls._config_file = config_path

    @classmethod
    def _load_config_file(cls) -> Dict[str, Any]:
        """加载配置文件"""
        if not cls._config_file:
            return {}

        config_path = Path(cls._config_file)
        if not config_path.exists():
            logger.warning(f"配置文件不存在: {cls._config_file}")
            return {}

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                if config_path.suffix.lower() in [".yaml", ".yml"]:
                    if yaml is None:
                        logger.warning("PyYAML 未安装，无法加载 YAML 配置文件")
                        return {}
                    return yaml.safe_load(f) or {}
                elif config_path.suffix.lower() == ".json":
                    return json.load(f)
                else:
                    logger.warning(f"不支持的配置文件格式: {config_path.suffix}")
                    return {}
        except Exception as e:
            logger.warning(f"加载配置文件失败: {e}")
            return {}

    @classmethod
    def _get_config_value(cls, key: str, default: Any) -> Any:
        """获取配置值，优先级：环境变量 > 配置文件 > 默认值"""
        env_value = os.getenv(key)
        if env_value is not None:
            return env_value

        if cls._initialized and cls._config_file:
            config_data = cls._load_config_file()
            if key in config_data:
                return config_data[key]

        return default

    @classmethod
    def init(cls):
        cls._initialized = True
        config_data = cls._load_config_file() if cls._config_file else {}

        cls.LOG_LEVEL = cls._get_config_value("LOG_LEVEL", cls.LOG_LEVEL)
        cls.MAX_RETRIES = int(cls._get_config_value("MAX_RETRIES", str(cls.MAX_RETRIES)))
        cls.RETRY_DELAY = int(cls._get_config_value("RETRY_DELAY", str(cls.RETRY_DELAY)))
        cls.COMMAND_TIMEOUT = int(
            cls._get_config_value("COMMAND_TIMEOUT", str(cls.COMMAND_TIMEOUT))
        )
        logger.debug(f"配置初始化完成: {cls.__name__}")

    @classmethod
    def get_config_info(cls) -> Dict[str, Any]:
        info = {
            "LOG_LEVEL": cls.LOG_LEVEL,
            "MAX_RETRIES": cls.MAX_RETRIES,
            "RETRY_DELAY": cls.RETRY_DELAY,
            "COMMAND_TIMEOUT": cls.COMMAND_TIMEOUT,
        }
        if cls._config_file:
            info["config_file"] = cls._config_file
        return info

    @classmethod
    def reload(cls):
        """重新加载配置"""
        cls._initialized = False
        cls.init()
        logger.info("配置已重新加载")
