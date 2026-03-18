"""
HarmonyOS Compile MCP 配置管理
"""

import os
from typing import Optional

from common.config.base import ConfigBase


class Config(ConfigBase):
    """MCP 编译工具配置类"""

    HARMONYOS_SDK_PATH: Optional[str] = os.getenv("HARMONYOS_SDK_PATH")
    HARMONYOS_TOOLS_PATH: Optional[str] = os.getenv("HARMONYOS_TOOLS_PATH")

    @classmethod
    def get_config_info(cls) -> dict:
        info = super().get_config_info()
        info.update(
            {
                "HARMONYOS_SDK_PATH": cls.HARMONYOS_SDK_PATH,
                "HARMONYOS_TOOLS_PATH": cls.HARMONYOS_TOOLS_PATH,
            }
        )
        return info
