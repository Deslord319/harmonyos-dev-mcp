"""
类型定义模块 - 编译工具专用

定义编译工具函数的输入输出类型。
"""
from typing import TypedDict, Optional, List

from common.types import BaseResult


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
