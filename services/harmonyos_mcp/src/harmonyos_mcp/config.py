"""
HarmonyOS MCP 配置管理

支持环境变量、自动检测工具路径。
"""
import os
import platform
import shutil
from pathlib import Path
from typing import Optional, List
from loguru import logger

from common.config.base import ConfigBase


class Config(ConfigBase):
    """HarmonyOS MCP 配置类"""

    DEVECO_STUDIO_PATH: Optional[str] = None
    HARMONYOS_SDK_PATH: Optional[str] = None
    HDC_PATH: Optional[str] = None
    HVIGOR_PATH: Optional[str] = None
    HILOGTOOL_PATH: Optional[str] = None
    NODE_PATH: Optional[str] = None
    DEFAULT_DEVICE_ID: Optional[str] = None

    UI_OPERATION_TIMEOUT: int = 5
    UI_TREE_TIMEOUT: int = 10
    BUILD_TIMEOUT: int = 600
    INSTALL_TIMEOUT: int = 120

    @classmethod
    def init(cls):
        super().init()
        system = platform.system()

        cls.DEVECO_STUDIO_PATH = os.getenv("DEVECO_STUDIO_PATH")
        cls.HARMONYOS_SDK_PATH = os.getenv("HARMONYOS_SDK_PATH")
        cls.HDC_PATH = os.getenv("HDC_PATH")
        cls.HILOGTOOL_PATH = os.getenv("HILOGTOOL_PATH")
        cls.DEFAULT_DEVICE_ID = os.getenv("HARMONYOS_DEVICE_ID")

        cls.UI_OPERATION_TIMEOUT = int(os.getenv("UI_OPERATION_TIMEOUT", str(cls.UI_OPERATION_TIMEOUT)))
        cls.UI_TREE_TIMEOUT = int(os.getenv("UI_TREE_TIMEOUT", str(cls.UI_TREE_TIMEOUT)))
        cls.BUILD_TIMEOUT = int(os.getenv("BUILD_TIMEOUT", str(cls.BUILD_TIMEOUT)))
        cls.INSTALL_TIMEOUT = int(os.getenv("INSTALL_TIMEOUT", str(cls.INSTALL_TIMEOUT)))

        if not cls.DEVECO_STUDIO_PATH:
            deveco_env = os.getenv("DevEco Studio")
            if deveco_env:
                deveco_env = deveco_env.split(";")[0].strip()
                if deveco_env:
                    path = Path(deveco_env)
                    if path.name.lower() == "bin":
                        path = path.parent
                    if path.exists():
                        cls.DEVECO_STUDIO_PATH = str(path)

        if not cls.HARMONYOS_SDK_PATH:
            candidates = []
            if cls.DEVECO_STUDIO_PATH:
                deveco = Path(cls.DEVECO_STUDIO_PATH)
                candidates.extend([deveco / "sdk", deveco.parent / "sdk"])
            user_home = Path.home()
            candidates.extend([
                user_home / "HarmonyOS" / "sdk",
                user_home / "AppData" / "Local" / "HarmonyOS" / "Sdk",
                user_home / "AppData" / "Local" / "Huawei" / "Sdk",
            ])
            for c in candidates:
                if c.exists():
                    cls.HARMONYOS_SDK_PATH = str(c)
                    break

        if not cls.HDC_PATH and cls.HARMONYOS_SDK_PATH:
            hdc_name = "hdc.exe" if system == "Windows" else "hdc"
            sdk = Path(cls.HARMONYOS_SDK_PATH)
            for subdir in ["toolchains", "openharmony/toolchains"]:
                hdc_path = sdk / subdir / hdc_name
                if hdc_path.exists():
                    cls.HDC_PATH = str(hdc_path)
                    break

        if not cls.HDC_PATH:
            hdc_in_path = shutil.which("hdc")
            if hdc_in_path:
                cls.HDC_PATH = hdc_in_path

        if cls.DEVECO_STUDIO_PATH:
            deveco = Path(cls.DEVECO_STUDIO_PATH)
            node_name = "node.exe" if system == "Windows" else "node"
            node_path = deveco / "tools" / "node" / node_name
            if node_path.exists():
                cls.NODE_PATH = str(node_path)

            hvigor_path = deveco / "tools" / "hvigor" / "bin" / "hvigorw.js"
            if hvigor_path.exists():
                cls.HVIGOR_PATH = str(hvigor_path)

        if not cls.HILOGTOOL_PATH and cls.HARMONYOS_SDK_PATH:
            hilogtool_name = "hilogtool.exe" if system == "Windows" else "hilogtool"
            sdk = Path(cls.HARMONYOS_SDK_PATH)
            for subdir in ["hms/toolchains", "toolchains"]:
                candidate = sdk / subdir / hilogtool_name
                if candidate.exists():
                    cls.HILOGTOOL_PATH = str(candidate)
                    break

        if cls.HDC_PATH:
            logger.info(f"hdc 路径: {cls.HDC_PATH}")
        if cls.NODE_PATH:
            logger.info(f"Node.js 路径: {cls.NODE_PATH}")
        if cls.HVIGOR_PATH:
            logger.info(f"hvigor 路径: {cls.HVIGOR_PATH}")
        if cls.HILOGTOOL_PATH:
            logger.info(f"hilogtool 路径: {cls.HILOGTOOL_PATH}")

    @classmethod
    def get_config_info(cls) -> dict:
        info = super().get_config_info()
        info.update({
            "DEVECO_STUDIO_PATH": cls.DEVECO_STUDIO_PATH,
            "HARMONYOS_SDK_PATH": cls.HARMONYOS_SDK_PATH,
            "HDC_PATH": cls.HDC_PATH,
            "NODE_PATH": cls.NODE_PATH,
            "HVIGOR_PATH": cls.HVIGOR_PATH,
            "HILOGTOOL_PATH": cls.HILOGTOOL_PATH,
            "DEFAULT_DEVICE_ID": cls.DEFAULT_DEVICE_ID,
        })
        return info


class LogSecurityConfig:
    """日志安全配置"""

    _ALLOWED_SAVE_PATHS_RELATIVE: List[str] = ["./hm_logs", "./hilog_files"]
    _ALLOWED_SAVE_PATHS_ABS: List[str] = []

    MAX_LOG_LINES: int = int(os.getenv("MAX_LOG_LINES", "50000"))
    MAX_OUTPUT_SIZE_MB: int = int(os.getenv("MAX_OUTPUT_SIZE_MB", "100"))
    DEFAULT_TIMEOUT: int = int(os.getenv("LOG_DEFAULT_TIMEOUT", "30"))
    MAX_TIMEOUT: int = int(os.getenv("LOG_MAX_TIMEOUT", "300"))
    FETCH_MULTIPLIER: int = int(os.getenv("LOG_FETCH_MULTIPLIER", "5"))
    ENABLE_NOISE_FILTER: bool = os.getenv("LOG_ENABLE_NOISE_FILTER", "true").lower() == "true"
    AUTO_CLEANUP_DAYS: int = int(os.getenv("LOG_AUTO_CLEANUP_DAYS", "7"))
    MAX_CACHE_SIZE_MB: int = int(os.getenv("LOG_MAX_CACHE_SIZE_MB", "500"))
    TIME_PARSE_STRATEGY: str = os.getenv("LOG_TIME_PARSE_STRATEGY", "auto")

    @classmethod
    def get_allowed_save_paths(cls) -> List[str]:
        if not cls._ALLOWED_SAVE_PATHS_ABS:
            cls._ALLOWED_SAVE_PATHS_ABS = [os.path.abspath(p) for p in cls._ALLOWED_SAVE_PATHS_RELATIVE]
        return cls._ALLOWED_SAVE_PATHS_ABS

    @classmethod
    def validate_save_path(cls, path: str) -> tuple:
        try:
            real_path = os.path.realpath(os.path.abspath(path))
            for allowed in cls.get_allowed_save_paths():
                if real_path.startswith(allowed + os.sep) or real_path == allowed:
                    os.makedirs(os.path.dirname(real_path) if os.path.splitext(real_path)[1] else real_path, exist_ok=True)
                    return True, real_path
            return False, f"路径不在白名单内。允许的路径: {cls.get_allowed_save_paths()}"
        except Exception as e:
            return False, f"路径验证失败: {e}"

    @classmethod
    def validate_timeout(cls, timeout: int) -> int:
        if timeout is None:
            return cls.DEFAULT_TIMEOUT
        return min(max(timeout, 1), cls.MAX_TIMEOUT)
