"""
hdc命令行工具封装

组合所有 Mixin 提供完整的 HarmonyOS 设备控制功能。
保持向后兼容的 API。

架构：
- HdcBase: 基础命令执行和 shell 校验
- HdcDeviceMixin: 设备管理（list_devices, install_app, uninstall_app）
- HdcAppMixin: 应用管理（start_app, get_app_pid, forward_port）
- HdcFileMixin: 文件操作（push_file, pull_file, hilog 相关）
- HdcUIMixin: UI 操作（get_window_list, get_ui_tree_raw, find_window_by_bundle）
- HdcPackageMixin: 包管理（list_packages, get_package_info, get_main_ability）
- HdcScreenshotMixin: 截图功能（take_screenshot, take_element_screenshot）
"""

from .hdc_base import HdcBase
from .hdc_device_mixin import HdcDeviceMixin
from .hdc_app_mixin import HdcAppMixin
from .hdc_file_mixin import HdcFileMixin
from .hdc_ui_mixin import HdcUIMixin
from .hdc_package_mixin import HdcPackageMixin
from .hdc_screenshot_mixin import HdcScreenshotMixin


class HdcWrapper(
    HdcBase,
    HdcDeviceMixin,
    HdcAppMixin,
    HdcFileMixin,
    HdcUIMixin,
    HdcPackageMixin,
    HdcScreenshotMixin
):
    """
    HarmonyOS Device Connector (hdc) 工具封装类
    
    组合所有功能模块，提供完整的设备控制能力：
    
    设备管理:
        - list_devices(): 列出连接的设备
        - install_app(): 安装应用
        - uninstall_app(): 卸载应用
    
    应用管理:
        - start_app(): 启动应用
        - get_app_pid(): 获取应用进程ID
        - forward_port(): 端口转发
    
    文件操作:
        - push_file(): 推送文件到设备
        - pull_file(): 从设备拉取文件
        - list_hilog_files(): 列出 hilog 文件
        - pull_hilog_files(): 拉取 hilog 文件
        - hilog_receive(): 获取所有 hilog 和 dict 文件
        - get_realtime_logs(): 获取实时日志
    
    UI 操作:
        - get_window_list(): 获取窗口列表
        - get_ui_tree_raw(): 获取 UI 组件树
        - find_window_by_bundle(): 根据包名查找窗口
    
    包管理:
        - list_packages(): 列出已安装的包
        - get_package_info(): 获取包详细信息
        - get_main_ability(): 获取主入口 Ability
    
    截图:
        - take_screenshot(): 全屏截图
        - take_element_screenshot(): 元素区域截图
    
    使用示例:
        hdc = HdcWrapper()
        devices = hdc.list_devices()
        hdc.take_screenshot(devices[0], './screenshot.png')
    """
    pass


# 向后兼容：导出所有相关类
__all__ = [
    'HdcWrapper',
    'HdcBase',
    'HdcDeviceMixin',
    'HdcAppMixin',
    'HdcFileMixin',
    'HdcUIMixin',
    'HdcPackageMixin',
    'HdcScreenshotMixin',
]
