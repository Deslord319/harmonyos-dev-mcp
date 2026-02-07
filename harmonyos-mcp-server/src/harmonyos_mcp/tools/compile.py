"""
三方库编译工具

提供 WSL 检查、库克隆、构建系统分析、脚本执行、输出验证等功能。
"""
from typing import Optional
from loguru import logger

from ..container import get_hdc, get_compile_manager
from ..types import (
    WslCheckResult, CompilerToolsResult, CloneLibraryResult,
    AnalyzeBuildResult, ReadBuildFilesResult, WriteScriptResult,
    ExecuteScriptResult, VerifyOutputResult
)
from .base import ToolBase


def check_wsl() -> WslCheckResult:
    """
    检查当前系统是否可用 WSL 环境（用于 Windows 下的交叉编译）

    Returns:
        WSL 检查结果
    """
    try:
        hdc = get_hdc()
        result = hdc.check_wsl_available()
        return result
    except Exception as e:
        return ToolBase.wrap_error(e, 'WSL_CHECK_ERROR')


def check_harmonyos_compiler_tools(tools_dir: str = "./harmonyos_commandline_tools") -> CompilerToolsResult:
    """
    检查 HarmonyOS Command Line Tools 是否已安装

    Args:
        tools_dir: 工具目录路径（默认当前目录的 harmonyos_commandline_tools）

    Returns:
        工具检查结果
    """
    try:
        hdc = get_hdc()
        result = hdc.check_harmonyos_compiler_tools(tools_dir)
        return result
    except Exception as e:
        return ToolBase.wrap_error(e, 'COMPILER_TOOLS_CHECK_ERROR')


def clone_library(repo_url: str, local_path: str, version: str = None) -> CloneLibraryResult:
    """
    拉取三方库代码仓库并切换到指定版本

    支持直接指定版本号克隆，避免下载完整历史记录，大幅提升速度。

    Args:
        repo_url: 库的 git 仓库 URL (支持 https/git 协议)
        local_path: 本地保存路径
        version: 可选，指定版本tag/branch（如 "v1.0.0", "main"）。
                指定版本时使用浅克隆(--depth 1)，大幅减少下载时间

    Returns:
        拉取结果，包含success状态、本地路径和克隆的版本信息
    """
    try:
        manager = get_compile_manager()
        result = manager.clone_library(repo_url, local_path, version)
        return result
    except Exception as e:
        return ToolBase.wrap_error(e, 'CLONE_LIBRARY_ERROR')


def analyze_build_system(project_dir: str) -> AnalyzeBuildResult:
    """
    分析三方库项目的构建系统类型

    Args:
        project_dir: 项目目录路径

    Returns:
        检测到的构建系统列表及其标记文件
    """
    try:
        manager = get_compile_manager()
        result = manager.analyze_build_system(project_dir)
        return result
    except Exception as e:
        return ToolBase.wrap_error(e, 'ANALYZE_BUILD_ERROR')


def read_build_files(project_dir: str) -> ReadBuildFilesResult:
    """
    读取项目的构建系统文件，供远端AI分析

    读取CMakeLists.txt、configure、Makefile等构建文件的内容，
    以及项目目录结构，返回给AI进行分析。

    Args:
        project_dir: 项目目录路径

    Returns:
        {
            "success": bool,
            "files": {文件名: 内容},
            "structure": "目录结构",
            "special_dirs": [特殊目录],
            "environment": {环境信息}
        }
    """
    try:
        from ..utils.compile_wrapper import get_build_file_reader, get_compile_environment
        reader = get_build_file_reader()
        env = get_compile_environment()

        result = reader.read_project_files(project_dir)
        result['success'] = True
        result['environment'] = env.get_environment_info()

        logger.info(f"读取构建文件: {len(result['files'])} 个文件")
        return result
    except Exception as e:
        return ToolBase.wrap_error(e, 'READ_BUILD_FILES_ERROR')


def write_compile_script(project_dir: str, script_content: str) -> WriteScriptResult:
    """
    将AI生成的编译脚本写入文件

    Args:
        project_dir: 项目目录
        script_content: 脚本内容（由AI生成的完整bash脚本）

    Returns:
        {
            "success": bool,
            "script_path": str,
            "message": str
        }
    """
    try:
        from ..utils.compile_wrapper import get_script_writer
        writer = get_script_writer()
        result = writer.write_script(project_dir, script_content)
        return result
    except Exception as e:
        return ToolBase.wrap_error(e, 'WRITE_SCRIPT_ERROR')


def execute_compile_script(script_path: str, timeout: int = 1800) -> ExecuteScriptResult:
    """
    执行编译脚本并返回输出

    Args:
        script_path: 脚本文件路径
        timeout: 超时时间（秒），默认30分钟

    Returns:
        {
            "success": bool,
            "exit_code": int,
            "stdout": str,
            "stderr": str,
            "duration": float
        }
    """
    try:
        from ..utils.compile_wrapper import get_script_executor
        executor = get_script_executor()
        result = executor.execute(script_path, timeout=timeout)
        return result
    except Exception as e:
        result = ToolBase.wrap_error(e, 'EXECUTE_SCRIPT_ERROR')
        result['exit_code'] = -1
        result['stdout'] = ''
        result['stderr'] = str(e)
        result['duration'] = 0
        return result


def verify_so_output(project_dir: str, output_dir: str = None) -> VerifyOutputResult:
    """
    验证编译输出的 .so 文件

    Args:
        project_dir: 项目目录路径
        output_dir: 输出目录（可选，默认为 project_dir/build_harmonyos）

    Returns:
        验证结果，包含文件检查、格式验证等信息
    """
    try:
        manager = get_compile_manager()
        result = manager.verify_so_output(
            project_dir=project_dir,
            output_dir=output_dir
        )
        return result
    except Exception as e:
        return ToolBase.wrap_error(e, 'VERIFY_SO_ERROR')
