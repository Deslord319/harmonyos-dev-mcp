"""
HarmonyOS Compile MCP 配置管理
"""
import os
from pathlib import Path
from typing import Optional
from loguru import logger

from common.config.base import ConfigBase


class Config(ConfigBase):
    """MCP 编译工具配置类"""

    HARMONYOS_SDK_PATH: Optional[str] = os.getenv("HARMONYOS_SDK_PATH")
    HARMONYOS_TOOLS_PATH: Optional[str] = os.getenv("HARMONYOS_TOOLS_PATH")
    CLONE_TIMEOUT: int = 300
    BUILD_TIMEOUT: int = 1800

    @classmethod
    def init(cls):
        super().init()

        cls.CLONE_TIMEOUT = int(os.getenv("CLONE_TIMEOUT", str(cls.CLONE_TIMEOUT)))
        cls.BUILD_TIMEOUT = int(os.getenv("BUILD_TIMEOUT", str(cls.BUILD_TIMEOUT)))

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
    def get_config_info(cls) -> dict:
        info = super().get_config_info()
        info.update({
            "HARMONYOS_SDK_PATH": cls.HARMONYOS_SDK_PATH,
            "HARMONYOS_TOOLS_PATH": cls.HARMONYOS_TOOLS_PATH,
            "CLONE_TIMEOUT": cls.CLONE_TIMEOUT,
            "BUILD_TIMEOUT": cls.BUILD_TIMEOUT,
        })
        return info
