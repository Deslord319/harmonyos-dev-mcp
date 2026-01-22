"""
配置管理模块

支持的环境变量:
    DEVECO_STUDIO_PATH  - DevEco Studio 安装路径
    HARMONYOS_SDK_PATH  - HarmonyOS SDK 路径
    HDC_PATH            - hdc 工具完整路径
    LOG_LEVEL           - 日志级别 (DEBUG, INFO, WARNING, ERROR)
"""
import os
import platform
import shutil
from pathlib import Path
from typing import Optional, List
from loguru import logger


class Config:
    """MCP Server配置类"""

    # ========================================================================
    # 环境变量配置（优先级最高）
    # ========================================================================

    # DevEco Studio 安装路径
    DEVECO_STUDIO_PATH: Optional[str] = os.getenv('DEVECO_STUDIO_PATH')

    # HarmonyOS SDK 路径
    HARMONYOS_SDK_PATH: Optional[str] = os.getenv('HARMONYOS_SDK_PATH')

    # hdc 工具完整路径
    HDC_PATH: Optional[str] = os.getenv('HDC_PATH')

    # hvigor 工具路径（自动检测）
    HVIGOR_PATH: Optional[str] = None

    # Node.js 路径（自动检测）
    NODE_PATH: Optional[str] = None

    # 默认设备ID
    DEFAULT_DEVICE_ID: Optional[str] = os.getenv('HARMONYOS_DEVICE_ID')

    # ========================================================================
    # 运行时配置
    # ========================================================================

    # 日志级别
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')

    # 超时设置(秒)
    COMMAND_TIMEOUT: int = int(os.getenv('COMMAND_TIMEOUT', '300'))
    BUILD_TIMEOUT: int = int(os.getenv('BUILD_TIMEOUT', '600'))
    INSTALL_TIMEOUT: int = int(os.getenv('INSTALL_TIMEOUT', '120'))

    # 重试设置
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 2

    # ========================================================================
    # 自动检测方法
    # ========================================================================

    @classmethod
    def _get_deveco_search_paths(cls) -> List[Path]:
        """获取 DevEco Studio 搜索路径列表"""
        paths = []
        system = platform.system()

        if system == "Windows":
            # Windows 常见安装路径
            paths.extend([
                Path("C:/Program Files/Huawei/DevEco Studio"),
                Path("C:/Program Files (x86)/Huawei/DevEco Studio"),
                Path(os.path.expanduser("~/AppData/Local/Huawei/DevEco Studio")),
                Path(os.path.expanduser("~/AppData/Local/Programs/Huawei/DevEco Studio")),
            ])
            # 尝试从注册表或常见位置检测
            program_files = os.environ.get('ProgramFiles', 'C:/Program Files')
            program_files_x86 = os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)')
            paths.extend([
                Path(program_files) / "Huawei" / "DevEco Studio",
                Path(program_files_x86) / "Huawei" / "DevEco Studio",
            ])
        elif system == "Darwin":
            # macOS 常见安装路径
            paths.extend([
                Path("/Applications/DevEco Studio.app/Contents"),
                Path(os.path.expanduser("~/Applications/DevEco Studio.app/Contents")),
            ])
        else:
            # Linux 常见安装路径
            paths.extend([
                Path(os.path.expanduser("~/DevEco Studio")),
                Path(os.path.expanduser("~/deveco-studio")),
                Path("/opt/DevEco Studio"),
                Path("/opt/deveco-studio"),
            ])

        # 去重
        return list(dict.fromkeys(paths))

    @classmethod
    def _get_sdk_search_paths(cls) -> List[Path]:
        """获取 SDK 搜索路径列表"""
        paths = []
        system = platform.system()

        # 如果已知 DevEco Studio 路径，优先从中查找
        if cls.DEVECO_STUDIO_PATH:
            deveco = Path(cls.DEVECO_STUDIO_PATH)
            paths.append(deveco / "sdk" / "default")
            paths.append(deveco / "sdk" / "HarmonyOS")

        if system == "Windows":
            paths.extend([
                Path(os.path.expanduser("~/AppData/Local/Huawei/Sdk")),
                Path(os.path.expanduser("~/Huawei/Sdk")),
            ])
            # 从 DevEco Studio 默认位置查找
            for deveco_path in cls._get_deveco_search_paths():
                paths.append(deveco_path / "sdk" / "default")
        elif system == "Darwin":
            paths.extend([
                Path(os.path.expanduser("~/Library/Huawei/Sdk")),
                Path(os.path.expanduser("~/Huawei/Sdk")),
            ])
        else:
            paths.extend([
                Path(os.path.expanduser("~/Huawei/Sdk")),
                Path(os.path.expanduser("~/.local/share/Huawei/Sdk")),
            ])

        return list(dict.fromkeys(paths))

    @classmethod
    def _find_hdc_in_sdk(cls, sdk_path: Path) -> Optional[str]:
        """在 SDK 路径中查找 hdc 工具"""
        system = platform.system()
        hdc_name = "hdc.exe" if system == "Windows" else "hdc"

        # 可能的 hdc 位置
        possible_paths = [
            sdk_path / "toolchains" / hdc_name,
            sdk_path / "openharmony" / "toolchains" / hdc_name,
            sdk_path / "HarmonyOS" / "toolchains" / hdc_name,
        ]

        for path in possible_paths:
            if path.exists():
                return str(path)

        return None

    @classmethod
    def init(cls):
        """初始化配置（自动检测工具路径）"""

        # 1. 检测 DevEco Studio 路径
        if not cls.DEVECO_STUDIO_PATH:
            for path in cls._get_deveco_search_paths():
                if path.exists():
                    cls.DEVECO_STUDIO_PATH = str(path)
                    logger.info(f"自动检测到 DevEco Studio: {path}")
                    break

        # 2. 检测 SDK 路径
        if not cls.HARMONYOS_SDK_PATH:
            for path in cls._get_sdk_search_paths():
                if path.exists():
                    cls.HARMONYOS_SDK_PATH = str(path)
                    logger.info(f"自动检测到 SDK: {path}")
                    break

        # 3. 检测 hdc 路径
        if not cls.HDC_PATH:
            # 首先尝试从 SDK 路径查找
            if cls.HARMONYOS_SDK_PATH:
                cls.HDC_PATH = cls._find_hdc_in_sdk(Path(cls.HARMONYOS_SDK_PATH))

            # 如果没找到，尝试从系统 PATH 查找
            if not cls.HDC_PATH:
                hdc_in_path = shutil.which('hdc')
                if hdc_in_path:
                    cls.HDC_PATH = hdc_in_path
                    logger.info(f"从 PATH 找到 hdc: {hdc_in_path}")

        # 4. 检测 Node.js 和 hvigor 路径（从 DevEco Studio）
        if cls.DEVECO_STUDIO_PATH:
            deveco = Path(cls.DEVECO_STUDIO_PATH)
            system = platform.system()

            # Node.js
            node_name = "node.exe" if system == "Windows" else "node"
            node_path = deveco / "tools" / "node" / node_name
            if node_path.exists():
                cls.NODE_PATH = str(node_path)

            # hvigor
            hvigor_path = deveco / "tools" / "hvigor" / "bin" / "hvigorw.js"
            if hvigor_path.exists():
                cls.HVIGOR_PATH = str(hvigor_path)

        if cls.HDC_PATH:
            logger.info(f"hdc 路径: {cls.HDC_PATH}")
        if cls.NODE_PATH:
            logger.info(f"Node.js 路径: {cls.NODE_PATH}")
        if cls.HVIGOR_PATH:
            logger.info(f"hvigor 路径: {cls.HVIGOR_PATH}")

    @classmethod
    def validate(cls) -> bool:
        """验证配置是否有效"""
        warnings = []
        errors = []

        if not cls.DEVECO_STUDIO_PATH:
            warnings.append("DEVECO_STUDIO_PATH 未设置，部分功能可能不可用")

        if not cls.HARMONYOS_SDK_PATH:
            warnings.append("HARMONYOS_SDK_PATH 未设置，将尝试自动检测")

        if not cls.HDC_PATH:
            errors.append("未找到 hdc 工具，请设置 HDC_PATH 环境变量或安装 DevEco Studio")

        # 打印警告
        for warning in warnings:
            print(f"⚠️  {warning}")

        # 打印错误
        for error in errors:
            print(f"❌  {error}")

        # 只要能找到 hdc 就允许启动
        return cls.HDC_PATH is not None

    @classmethod
    def get_config_info(cls) -> dict:
        """获取当前配置信息（用于调试）"""
        return {
            "DEVECO_STUDIO_PATH": cls.DEVECO_STUDIO_PATH,
            "HARMONYOS_SDK_PATH": cls.HARMONYOS_SDK_PATH,
            "HDC_PATH": cls.HDC_PATH,
            "NODE_PATH": cls.NODE_PATH,
            "HVIGOR_PATH": cls.HVIGOR_PATH,
            "DEFAULT_DEVICE_ID": cls.DEFAULT_DEVICE_ID,
            "LOG_LEVEL": cls.LOG_LEVEL,
            "platform": platform.system(),
        }


# 初始化配置
Config.init()

