"""
类型定义模块

定义所有工具函数的输入输出类型，提供完整的类型提示支持。
"""
from typing import TypedDict, Optional, List, Literal, Any
from dataclasses import dataclass


# ============================================================================
# 通用响应类型
# ============================================================================

class BaseResult(TypedDict, total=False):
    """所有工具返回的基础类型"""
    success: bool
    error: str
    message: str


class DeviceResult(BaseResult):
    """设备相关操作结果基类"""
    device_id: str


# ============================================================================
# 设备管理类型
# ============================================================================

class DeviceInfo(TypedDict):
    """设备信息"""
    device_id: str
    status: str
    model: Optional[str]


class ListDevicesResult(BaseResult):
    """list_devices 返回类型"""
    devices: List[str]
    count: int


class HilogReceiveResult(DeviceResult):
    """hilog_receive 返回类型"""
    files: List[str]
    total_size: int


class ScreenshotResult(DeviceResult):
    """take_screenshot 返回类型"""
    local_path: str
    file_size: int


class ElementScreenshotResult(DeviceResult):
    """take_element_screenshot 返回类型"""
    local_path: str
    file_size: int
    bounds: dict
    warning: Optional[str]


# ============================================================================
# 构建部署类型
# ============================================================================

class BuildResult(BaseResult):
    """build_app 返回类型"""
    hap_path: Optional[str]
    duration: Optional[float]


class InstallResult(DeviceResult):
    """install_app 返回类型"""
    hap_path: str


class RunAppResult(DeviceResult):
    """run_app 返回类型"""
    bundle_name: str
    ability_name: str
    module_name: str
    auto_detected: bool
    command_success: bool
    window_found: bool
    window: Optional[dict]


class UninstallResult(DeviceResult):
    """uninstall_app 返回类型"""
    bundle_name: str


# ============================================================================
# 包管理类型
# ============================================================================

class AbilityInfo(TypedDict, total=False):
    """Ability 信息"""
    name: str
    module: str
    type: str


class ListPackagesResult(DeviceResult):
    """list_packages 返回类型"""
    packages: List[str]
    count: int


class PackageAbilitiesResult(DeviceResult):
    """get_package_abilities 返回类型"""
    bundle_name: str
    abilities: List[AbilityInfo]
    modules: List[str]
    main_ability: Optional[AbilityInfo]
    ability_count: int


class MainAbilityResult(DeviceResult):
    """get_main_ability 返回类型"""
    bundle_name: str
    ability_name: str
    module_name: str


# ============================================================================
# UI 操作类型
# ============================================================================

class UIElement(TypedDict, total=False):
    """UI 元素"""
    id: str
    type: str
    text: str
    x: int
    y: int
    width: int
    height: int
    bounds: dict
    clickable: bool
    visible: bool


class Bounds(TypedDict):
    """元素边界"""
    left: int
    top: int
    right: int
    bottom: int


class FindElementResult(DeviceResult):
    """find_element 返回类型"""
    elements: List[UIElement]
    count: int


class ClickResult(BaseResult):
    """点击操作返回类型"""
    x: int
    y: int


class SwipeResult(BaseResult):
    """滑动操作返回类型"""
    from_x: int
    from_y: int
    to_x: int
    to_y: int
    direction: Optional[str]


class InputTextResult(BaseResult):
    """输入文本返回类型"""
    text: str
    x: int
    y: int


class PressKeyResult(BaseResult):
    """按键操作返回类型"""
    key: str


# ============================================================================
# UI 树类型
# ============================================================================

class UITreeNode(TypedDict, total=False):
    """UI 树节点"""
    type: str
    id: str
    text: str
    bounds: Bounds
    children: List['UITreeNode']
    attributes: dict


class UITreeResult(DeviceResult):
    """get_ui_tree 返回类型"""
    window_id: int
    ui_tree: dict
    node_count: int


class WindowInfo(TypedDict):
    """窗口信息"""
    window_id: int
    bundle_name: str
    is_visible: bool
    bounds: Bounds


class ListWindowsResult(DeviceResult):
    """list_windows 返回类型"""
    windows: List[WindowInfo]
    count: int


# ============================================================================
# 日志类型
# ============================================================================

LogLevel = Literal['D', 'I', 'W', 'E', 'F']
AnalysisType = Literal['summary', 'errors', 'performance', 'crashes', 'keywords', 'custom']


class LogsFilterConfig(TypedDict, total=False):
    """日志过滤配置"""
    level: LogLevel
    tag: str
    keyword: str
    pid: int
    package_name: str
    seconds: int
    start_time: str
    end_time: str
    time_range: Optional[dict]


class LogsSummary(TypedDict, total=False):
    """日志摘要"""
    level_stats: dict
    time_range: Optional[dict]
    top_tags: List[str]
    error_count: int


class LogsFetchResult(DeviceResult):
    """logs_fetch 返回类型"""
    logs: List[str]
    total_lines: int
    truncated: bool
    filters_applied: LogsFilterConfig
    summary: LogsSummary
    source: str          # "realtime_buffer" | "persist_file"
    dict_used: bool      # 历史文件是否使用 dict 解密
    files_count: int     # 历史文件拉取数量


class LogsSaveResult(DeviceResult):
    """logs_save_snapshot 返回类型"""
    saved_path: str
    file_size: int
    file_size_human: str
    log_count: int
    truncated: bool


class LogsAnalyzeResult(DeviceResult):
    """logs_analyze 返回类型"""
    analysis_type: AnalysisType
    result: dict
    evidence_lines: List[str]
    total_entries_analyzed: int
    filters_applied: LogsFilterConfig


# ============================================================================
# 三方库编译类型
# ============================================================================

class WslCheckResult(BaseResult):
    """check_wsl 返回类型"""
    wsl_available: bool
    wsl_version: Optional[str]
    distributions: List[str]


class CompilerToolsResult(BaseResult):
    """check_harmonyos_compiler_tools 返回类型"""
    tools_found: bool
    tools_path: str
    components: dict


class CloneLibraryResult(BaseResult):
    """clone_library 返回类型"""
    local_path: str
    version: Optional[str]
    cloned_at: str


class BuildSystemInfo(TypedDict):
    """构建系统信息"""
    type: str
    marker_file: str
    confidence: float


class AnalyzeBuildResult(BaseResult):
    """analyze_build_system 返回类型"""
    build_systems: List[BuildSystemInfo]
    primary_system: Optional[str]


class ReadBuildFilesResult(BaseResult):
    """read_build_files 返回类型"""
    files: dict
    structure: str
    special_dirs: List[str]
    environment: dict


class WriteScriptResult(BaseResult):
    """write_compile_script 返回类型"""
    script_path: str


class ExecuteScriptResult(BaseResult):
    """execute_compile_script 返回类型"""
    exit_code: int
    stdout: str
    stderr: str
    duration: float


class VerifyOutputResult(BaseResult):
    """verify_so_output 返回类型"""
    so_files: List[str]
    verified: bool
    architecture: str
    file_sizes: dict


# ============================================================================
# 工具定义类型（用于插件系统）
# ============================================================================

@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    func: Any  # Callable
    description: str
    category: str
