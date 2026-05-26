"""Shared result and payload type definitions for harmonyos_dev_mcp."""

from typing import List, Literal, Optional, TypedDict

from common.types import BaseResult


class DeviceResult(BaseResult, total=False):
    device_id: str


class DeviceInfo(TypedDict, total=False):
    device_id: str
    model: str
    device_name: str
    os_version: str
    api_version: str
    screen_size: str


class ListDevicesResult(BaseResult):
    devices: List[DeviceInfo]
    count: int


class ScreenshotResult(DeviceResult):
    local_path: str
    file_size: int


class ElementScreenshotResult(DeviceResult):
    local_path: str
    file_size: int
    bounds: dict
    warning: Optional[str]


class BuildError(TypedDict, total=False):
    file: Optional[str]
    line: int
    column: int
    message: str
    type: str
    source: str


class BuildResult(BaseResult):
    output_path: Optional[str]
    hsp_output_paths: Optional[List[str]]
    target: Optional[str]
    duration: Optional[float]
    errors: Optional[List[BuildError]]
    error_count: Optional[int]


class InstallResult(DeviceResult):
    hap_path: str


class RunAppResult(DeviceResult):
    bundle_name: str
    ability_name: str
    module_name: str
    auto_detected: bool
    command_success: bool
    window_found: bool
    window: Optional[dict]


class UninstallResult(DeviceResult):
    bundle_name: str


class AbilityInfo(TypedDict, total=False):
    name: str
    module: str
    type: str


QueryInfoType = Literal["list", "abilities", "main_ability", "permissions"]


class QueryPackageResult(DeviceResult, total=False):
    info_type: QueryInfoType
    packages: List[str]
    count: int
    keyword: str
    bundle_name: str
    abilities: List[AbilityInfo]
    modules: List[str]
    main_ability: Optional[AbilityInfo]
    ability_count: int
    ability_name: str
    module_name: str
    candidates: List[dict]
    recommended: int
    requested_permissions: List[str]
    permission_count: int


class UIElement(TypedDict, total=False):
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
    compid: str
    depth: int
    element_handle: dict
    lookup_is_broad: bool


class Bounds(TypedDict):
    left: int
    top: int
    right: int
    bottom: int


class FindElementResult(DeviceResult):
    elements: List[UIElement]
    count: int


WaitElementState = Literal["found", "gone"]


class WaitElementResult(DeviceResult, total=False):
    state: WaitElementState
    satisfied: bool
    elapsed_ms: int
    element: Optional[UIElement]


class ClickResult(BaseResult):
    x: int
    y: int


class LongPressResult(BaseResult):
    x: int
    y: int


class DragResult(BaseResult):
    from_x: int
    from_y: int
    to_x: int
    to_y: int


class SwipeResult(BaseResult):
    from_x: int
    from_y: int
    to_x: int
    to_y: int
    direction: Optional[str]


class InputTextResult(BaseResult):
    text: str
    x: int
    y: int


class PressKeyResult(BaseResult):
    key: str


class UITreeNode(TypedDict, total=False):
    type: str
    id: str
    text: str
    bounds: Bounds
    children: List["UITreeNode"]
    attributes: dict


class UITreeResult(DeviceResult):
    window_id: int
    validated_window_id: Optional[int]
    validation_applied: bool
    capture_scope: str
    ui_tree: dict
    node_count: int


class WindowInfo(TypedDict):
    window_id: int
    bundle_name: str
    bundle_name_resolved: bool
    is_visible: bool
    bounds: Bounds


class ListWindowsResult(DeviceResult):
    windows: List[WindowInfo]
    count: int


LogLevel = Literal["D", "I", "W", "E", "F"]
LogQueryMode = Literal["errors", "markers"]


class LogsFilterConfig(TypedDict, total=False):
    mode: LogQueryMode
    level: LogLevel
    tag: str
    tag_search: str
    keyword: str
    domain: str
    pid: int
    package_name: str
    seconds: int
    start_time: str
    end_time: str
    marker_keywords: List[str]

class LogQueryItem(TypedDict, total=False):
    type: str
    severity: int
    score: int
    timestamp: Optional[str]
    level: Optional[str]
    tag: Optional[str]
    pid: Optional[int]
    message: str
    raw_line: str
    context_before: List[str]
    context_after: List[str]
    matched_keywords: List[str]
    match_strength: str
    matched_keyword_types: dict
    group_key: str
    group_score: int
    related_items: List[dict]
    error_keywords: List[str]
    suspicious_keywords: List[str]


class LogsQueryResult(BaseResult, total=False):
    query_mode: LogQueryMode
    device_id: str
    source_attempted: List[str]
    source_used: str
    fallback_triggered: bool
    matched: bool
    match_count: int
    group_count: int
    items: List[LogQueryItem]
    filters_applied: LogsFilterConfig
    saved_path: str
    dict_used: bool
    dict_status: str
    files_count: int
    crash_info: dict

