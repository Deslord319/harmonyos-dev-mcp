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

    # 初始化标记
    _initialized: bool = False

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

    # hilogtool 工具路径（用于解析历史 hilog 文件）
    HILOGTOOL_PATH: Optional[str] = os.getenv('HILOGTOOL_PATH')

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
    UI_OPERATION_TIMEOUT: int = int(os.getenv('UI_OPERATION_TIMEOUT', '5'))    # UI操作(点击/滑动等)
    UI_TREE_TIMEOUT: int = int(os.getenv('UI_TREE_TIMEOUT', '10'))             # UI树获取
    COMMAND_TIMEOUT: int = int(os.getenv('COMMAND_TIMEOUT', '30'))             # 通用命令
    BUILD_TIMEOUT: int = int(os.getenv('BUILD_TIMEOUT', '600'))
    INSTALL_TIMEOUT: int = int(os.getenv('INSTALL_TIMEOUT', '120'))

    # 重试设置
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 2

    # ========================================================================
    # 初始化方法
    # ========================================================================

    @classmethod
    def ensure_init(cls):
        """确保配置已初始化（懒加载入口）"""
        if not cls._initialized:
            cls.init()

    @classmethod
    def init(cls):
        """初始化配置（从环境变量或PATH检测工具路径）"""
        cls._initialized = True
        system = platform.system()

        # 1. 检测 DevEco Studio 路径（仅从 "DevEco Studio" 环境变量）
        if not cls.DEVECO_STUDIO_PATH:
            deveco_env = os.getenv('DevEco Studio')
            if deveco_env:
                deveco_env = deveco_env.split(';')[0].strip()
                if deveco_env:
                    deveco_path = Path(deveco_env)
                    if deveco_path.name.lower() == 'bin':
                        deveco_path = deveco_path.parent
                    if deveco_path.exists():
                        cls.DEVECO_STUDIO_PATH = str(deveco_path)
                        logger.debug(f"从环境变量 'DevEco Studio' 检测到: {deveco_path}")

        # 2. 检测 HarmonyOS SDK 路径
        if not cls.HARMONYOS_SDK_PATH:
            sdk_candidates = []
            # 从 DevEco Studio 路径推断
            if cls.DEVECO_STUDIO_PATH:
                deveco = Path(cls.DEVECO_STUDIO_PATH)
                sdk_candidates.append(deveco / "sdk")
                sdk_candidates.append(deveco.parent / "sdk")
            # 用户目录下常见位置
            user_home = Path.home()
            sdk_candidates.extend([
                user_home / "HarmonyOS" / "sdk",
                user_home / "AppData" / "Local" / "HarmonyOS" / "Sdk",
                user_home / "AppData" / "Local" / "Huawei" / "Sdk",
                user_home / ".harmonyos" / "sdk",
            ])
            for candidate in sdk_candidates:
                if candidate.exists() and candidate.is_dir():
                    cls.HARMONYOS_SDK_PATH = str(candidate)
                    logger.debug(f"自动检测到 SDK 路径: {candidate}")
                    break

        # 3. 检测 hdc 路径
        if not cls.HDC_PATH:
            # 从 SDK 路径查找
            if cls.HARMONYOS_SDK_PATH:
                hdc_name = "hdc.exe" if system == "Windows" else "hdc"
                sdk = Path(cls.HARMONYOS_SDK_PATH)
                for subdir in ["toolchains", "openharmony/toolchains", "HarmonyOS/toolchains"]:
                    hdc_path = sdk / subdir / hdc_name
                    if hdc_path.exists():
                        cls.HDC_PATH = str(hdc_path)
                        break

            # 从系统 PATH 查找
            if not cls.HDC_PATH:
                hdc_in_path = shutil.which('hdc')
                if hdc_in_path:
                    cls.HDC_PATH = hdc_in_path
                    logger.info(f"从 PATH 找到 hdc: {hdc_in_path}")

        # 3. 检测 Node.js 和 hvigor（从 DevEco Studio）
        if cls.DEVECO_STUDIO_PATH:
            deveco = Path(cls.DEVECO_STUDIO_PATH)
            node_name = "node.exe" if system == "Windows" else "node"
            node_path = deveco / "tools" / "node" / node_name
            if node_path.exists():
                cls.NODE_PATH = str(node_path)

            hvigor_path = deveco / "tools" / "hvigor" / "bin" / "hvigorw.js"
            if hvigor_path.exists():
                cls.HVIGOR_PATH = str(hvigor_path)

        # 4. 检测 hilogtool 路径
        if not cls.HILOGTOOL_PATH and cls.HARMONYOS_SDK_PATH:
            hilogtool_name = "hilogtool.exe" if system == "Windows" else "hilogtool"
            sdk = Path(cls.HARMONYOS_SDK_PATH)
            for subdir in ["hms/toolchains", "toolchains", "openharmony/toolchains"]:
                candidate = sdk / subdir / hilogtool_name
                if candidate.exists():
                    cls.HILOGTOOL_PATH = str(candidate)
                    break

        # 输出检测结果
        if cls.HDC_PATH:
            logger.info(f"hdc 路径: {cls.HDC_PATH}")
        if cls.NODE_PATH:
            logger.info(f"Node.js 路径: {cls.NODE_PATH}")
        if cls.HVIGOR_PATH:
            logger.info(f"hvigor 路径: {cls.HVIGOR_PATH}")
        if cls.HILOGTOOL_PATH:
            logger.info(f"hilogtool 路径: {cls.HILOGTOOL_PATH}")

    @classmethod
    def validate(cls) -> bool:
        """验证配置是否有效"""
        hints = []
        errors = []

        if not cls.DEVECO_STUDIO_PATH:
            hints.append("DEVECO_STUDIO_PATH 未设置，部分功能可能不可用")

        if not cls.HARMONYOS_SDK_PATH:
            hints.append("HARMONYOS_SDK_PATH 未检测到，部分功能可能不可用")

        if not cls.HDC_PATH:
            errors.append("未找到 hdc 工具，请设置 HDC_PATH 环境变量或安装 DevEco Studio")

        for hint in hints:
            logger.debug(hint)
        for error in errors:
            logger.error(error)

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
            "HILOGTOOL_PATH": cls.HILOGTOOL_PATH,
            "DEFAULT_DEVICE_ID": cls.DEFAULT_DEVICE_ID,
            "LOG_LEVEL": cls.LOG_LEVEL,
            "platform": platform.system(),
        }



class LogSecurityConfig:
    """日志安全配置类"""
    
    # 日志保存白名单路径（必须使用绝对路径，防止路径遍历攻击）
    # 注意：这些类初始化时转换为绝对路径
    _ALLOWED_SAVE_PATHS_RELATIVE: List[str] = [
        "./hm_logs",
        "./hilog_files",
    ]

    # 缓存转换后的绝对路径
    _ALLOWED_SAVE_PATHS_ABS: List[str] = []

    @classmethod
    def get_allowed_save_paths(cls) -> List[str]:
        """获取绝对路径形式的白名单目录"""
        if not cls._ALLOWED_SAVE_PATHS_ABS:
            cls._ALLOWED_SAVE_PATHS_ABS = [
                os.path.abspath(p) for p in cls._ALLOWED_SAVE_PATHS_RELATIVE
            ]
        return cls._ALLOWED_SAVE_PATHS_ABS
    
    # 最大日志行数限制
    MAX_LOG_LINES: int = int(os.getenv('MAX_LOG_LINES', '50000'))
    
    # 最大输出大小（MB）
    MAX_OUTPUT_SIZE_MB: int = int(os.getenv('MAX_OUTPUT_SIZE_MB', '100'))
    
    # 默认超时（秒）
    DEFAULT_TIMEOUT: int = int(os.getenv('LOG_DEFAULT_TIMEOUT', '30'))
    
    # 最大超时（秒）
    MAX_TIMEOUT: int = int(os.getenv('LOG_MAX_TIMEOUT', '300'))
    
    @classmethod
    def validate_save_path(cls, path: str) -> tuple:
        """
        验证保存路径是否在白名单内

        使用 realpath 解析符号链接，防止通过 symlink 绕过白名单。
        使用绝对路径白名单，防止路径遍历攻击。

        Args:
            path: 要验证的路径

        Returns:
            (是否有效, 绝对路径或错误信息)
        """
        try:
            # realpath 同时解析符号链接和相对路径，比 abspath 更安全
            real_path = os.path.realpath(os.path.abspath(path))

            # 获取绝对路径白名单
            allowed_paths = cls.get_allowed_save_paths()

            # 验证路径是否在白名单内
            for allowed in allowed_paths:
                if real_path.startswith(allowed + os.sep) or real_path == allowed:
                    # 确保目录存在
                    os.makedirs(os.path.dirname(real_path) if os.path.splitext(real_path)[1] else real_path, exist_ok=True)
                    return True, real_path

            return False, f"路径不在白名单内。允许的路径: {allowed_paths}"
        except Exception as e:
            return False, f"路径验证失败: {e}"
    
    @classmethod
    def validate_timeout(cls, timeout: int) -> int:
        """验证并限制超时值"""
        if timeout is None:
            return cls.DEFAULT_TIMEOUT
        return min(max(timeout, 1), cls.MAX_TIMEOUT)