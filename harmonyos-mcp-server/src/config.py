"""
配置管理模块
"""
import os
from pathlib import Path
from typing import Optional


class Config:
    """MCP Server配置类"""
    
    # HarmonyOS SDK路径
    HARMONYOS_SDK_PATH: Optional[str] = os.getenv('HARMONYOS_SDK_PATH')
    
    # hdc工具路径
    HDC_PATH: Optional[str] = None
    
    # hvigor工具路径
    HVIGOR_PATH: Optional[str] = None
    
    # 默认设备ID
    DEFAULT_DEVICE_ID: Optional[str] = None
    
    # HTTP服务端口(用于UI树获取)
    UI_TREE_PORT: int = 8080
    
    # 日志级别
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    
    # 超时设置(秒)
    COMMAND_TIMEOUT: int = 300
    BUILD_TIMEOUT: int = 600
    INSTALL_TIMEOUT: int = 120
    
    # 重试设置
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 2
    
    @classmethod
    def init(cls):
        """初始化配置"""
        # 尝试自动检测SDK路径
        if not cls.HARMONYOS_SDK_PATH:
            # 尝试常见的SDK安装路径
            common_paths = [
                r"C:\Program Files\Huawei\DevEco Studio\sdk\default",
                r"C:\Users\admin\AppData\Local\Huawei\Sdk",
                os.path.expanduser("~/Library/Huawei/Sdk"),  # macOS
                os.path.expanduser("~/Huawei/Sdk"),  # Linux
            ]
            for path in common_paths:
                if os.path.exists(path):
                    cls.HARMONYOS_SDK_PATH = path
                    break

        # 自动检测hdc路径
        if cls.HARMONYOS_SDK_PATH:
            sdk_path = Path(cls.HARMONYOS_SDK_PATH)

            # Windows - 尝试多个可能的路径
            possible_paths = [
                sdk_path / 'toolchains' / 'hdc.exe',
                sdk_path / 'openharmony' / 'toolchains' / 'hdc.exe',
            ]
            for hdc_path in possible_paths:
                if hdc_path.exists():
                    cls.HDC_PATH = str(hdc_path)
                    break

            # Linux/Mac
            if not cls.HDC_PATH:
                hdc_unix = sdk_path / 'toolchains' / 'hdc'
                if hdc_unix.exists():
                    cls.HDC_PATH = str(hdc_unix)

        # 如果没有找到,尝试从PATH中查找
        if not cls.HDC_PATH:
            import shutil
            hdc_in_path = shutil.which('hdc')
            if hdc_in_path:
                cls.HDC_PATH = hdc_in_path
    
    @classmethod
    def validate(cls) -> bool:
        """验证配置是否有效"""
        warnings = []

        if not cls.HARMONYOS_SDK_PATH:
            warnings.append("HARMONYOS_SDK_PATH 未设置，将尝试自动检测")

        if not cls.HDC_PATH:
            warnings.append("未找到hdc工具，部分功能可能不可用")

        # 打印警告但不阻止启动
        for warning in warnings:
            print(f"⚠️  {warning}")

        # 只要能找到hdc就允许启动
        return cls.HDC_PATH is not None


# 初始化配置
Config.init()

