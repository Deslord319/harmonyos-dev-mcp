"""
配置管理模块 - 编译工具专用
"""

import os
from pathlib import Path
from typing import Optional
from loguru import logger


class Config:
    """MCP 编译工具配置类"""

    # 初始化标记
    _initialized: bool = False

    # HarmonyOS SDK 路径
    HARMONYOS_SDK_PATH: Optional[str] = os.getenv("HARMONYOS_SDK_PATH")

    # HarmonyOS Command Line Tools 路径
    HARMONYOS_TOOLS_PATH: Optional[str] = os.getenv("HARMONYOS_TOOLS_PATH")

    # 日志级别
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # 超时设置(秒)
    COMMAND_TIMEOUT: int = int(os.getenv("COMMAND_TIMEOUT", "30"))
    CLONE_TIMEOUT: int = int(os.getenv("CLONE_TIMEOUT", "300"))
    BUILD_TIMEOUT: int = int(os.getenv("BUILD_TIMEOUT", "1800"))

    # 重试设置
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 2

    @classmethod
    def ensure_init(cls):
        """确保配置已初始化（懒加载入口）"""
        if not cls._initialized:
            cls.init()

    @classmethod
    def init(cls):
        """初始化配置"""
        cls._initialized = True

        # 自动检测 HarmonyOS SDK 路径
        if not cls.HARMONYOS_SDK_PATH:
            user_home = Path.home()
            sdk_candidates = [
                user_home / "HarmonyOS" / "sdk",
                user_home / "AppData" / "Local" / "HarmonyOS" / "Sdk",
                user_home / "AppData" / "Local" / "Huawei" / "Sdk",
                user_home / ".harmonyos" / "sdk",
            ]
            for candidate in sdk_candidates:
                if candidate.exists() and candidate.is_dir():
                    cls.HARMONYOS_SDK_PATH = str(candidate)
                    logger.debug(f"自动检测到 SDK 路径: {candidate}")
                    break

        # 自动检测 Command Line Tools 路径
        if not cls.HARMONYOS_TOOLS_PATH:
            user_home = Path.home()
            tools_candidates = [
                Path.cwd() / "harmonyos_commandline_tools",
                user_home / "harmonyos_commandline_tools",
            ]
            for candidate in tools_candidates:
                if candidate.exists() and candidate.is_dir():
                    cls.HARMONYOS_TOOLS_PATH = str(candidate)
                    logger.debug(f"自动检测到工具路径: {candidate}")
                    break

        logger.info(f"SDK 路径: {cls.HARMONYOS_SDK_PATH}")
        logger.info(f"工具路径: {cls.HARMONYOS_TOOLS_PATH}")

    @classmethod
    def validate(cls) -> bool:
        """验证配置是否有效"""
        if not cls.HARMONYOS_SDK_PATH:
            logger.warning("HARMONYOS_SDK_PATH 未设置")

        if not cls.HARMONYOS_TOOLS_PATH:
            logger.warning("HARMONYOS_TOOLS_PATH 未设置")

        return True

    @classmethod
    def get_config_info(cls) -> dict:
        """获取当前配置信息"""
        return {
            "HARMONYOS_SDK_PATH": cls.HARMONYOS_SDK_PATH,
            "HARMONYOS_TOOLS_PATH": cls.HARMONYOS_TOOLS_PATH,
            "LOG_LEVEL": cls.LOG_LEVEL,
        }
