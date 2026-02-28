"""
构建部署工具

提供应用构建、安装、运行、卸载等功能。
"""
import asyncio
import time
from pathlib import Path
from typing import Optional
from loguru import logger

from ..container import get_hdc
from ..utils.wrappers.hvigor_wrapper import HvigorWrapper
from ..types import BuildResult, InstallResult, RunAppResult, UninstallResult
from .device_base import ToolBase
from common.tools.registry import mcp_tool


@mcp_tool(category="build")
@ToolBase.handle_tool_error('BUILD_ERROR', hap_path=None, duration=0)
async def build_app(project_path: str, build_mode: str = "debug") -> BuildResult:
    """
    构建HarmonyOS应用

    Args:
        project_path: 项目路径
        build_mode: 构建模式 (debug/release)

    Returns:
        构建结果:
        - success: 是否成功
        - hap_path: HAP 包路径
        - message: 构建消息
        - duration: 耗时（秒）
    """
    start_time = time.time()

    hvigor = HvigorWrapper(project_path)
    result = await asyncio.to_thread(hvigor.build_hap, build_mode=build_mode)
    elapsed = time.time() - start_time

    response: BuildResult = {
        'success': result['success'],
        'hap_path': result.get('hap_path'),
        'message': f"构建{'成功' if result['success'] else '失败'}，耗时: {ToolBase.format_duration(elapsed)}",
        'duration': elapsed
    }

    # 构建失败时提取错误信息
    if not result['success']:
        error_msg = _extract_build_error(project_path)
        if error_msg:
            response['error'] = error_msg

    return response


def _extract_build_error(project_path: str) -> Optional[str]:
    """
    从构建日志中提取错误信息
    
    Args:
        project_path: 项目路径
        
    Returns:
        错误信息字符串，如果没有找到则返回 None
    """
    try:
        log_file = Path(project_path) / '.hvigor' / 'outputs' / 'build-logs' / 'build.log'
        if not log_file.exists():
            return None

        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            # 查找错误信息
            error_lines = [
                line.strip() for line in lines
                if 'ERROR' in line or 'Error Message' in line
            ]
            return '\n'.join(error_lines[-3:]) if error_lines else None
    except Exception as e:
        logger.debug(f"读取构建日志失败: {e}")
        return None


@mcp_tool(category="build")
@ToolBase.handle_tool_error('INSTALL_ERROR', hap_path='')
@ToolBase.with_device(hap_path='')
async def install_app(hap_path: str, device_id: Optional[str] = None) -> InstallResult:
    """
    安装应用到设备

    Args:
        hap_path: HAP包路径
        device_id: 设备ID,如果为None则使用第一个设备

    Returns:
        安装结果:
        - success: 是否成功
        - device_id: 设备ID
        - hap_path: HAP包路径
    """
    hdc = get_hdc()
    success = await asyncio.to_thread(hdc.install_app, device_id, hap_path)

    return {
        'success': success,
        'device_id': device_id,
        'hap_path': hap_path
    }


@mcp_tool(category="build")
@ToolBase.handle_tool_error('RUN_APP_ERROR', bundle_name='', ability_name='', module_name='entry', auto_detected=False, command_success=False, window_found=False, window=None)
@ToolBase.with_device(bundle_name='', ability_name='', module_name='entry', auto_detected=False, command_success=False, window_found=False, window=None)
async def run_app(
    bundle_name: str,
    device_id: Optional[str] = None,
    ability_name: Optional[str] = None,
    module_name: Optional[str] = None,
    auto_detect: bool = True
) -> RunAppResult:
    """
    运行应用

    Args:
        bundle_name: 应用包名
        device_id: 设备ID,如果为None则使用第一个设备
        ability_name: Ability名称,如果为None且auto_detect=True则自动检测主Ability
        module_name: 模块名称,如果为None且auto_detect=True则自动检测
        auto_detect: 是否自动检测主Ability(默认True)

    Returns:
        运行结果

    Example:
        # 自动检测主Ability并启动
        run_app(bundle_name="com.huawei.hmos.settings")

        # 指定Ability启动
        run_app(bundle_name="com.example.app", ability_name="MainAbility", module_name="entry")
    """
    hdc = get_hdc()

    # 解析 Ability 信息
    final_ability, final_module, auto_detected = await asyncio.to_thread(
        _resolve_ability, hdc, device_id, bundle_name, ability_name, module_name, auto_detect
    )

    start_result = await asyncio.to_thread(hdc.start_app, device_id, bundle_name, final_ability, final_module)

    result = {
        'success': start_result['success'],
        'device_id': device_id,
        'bundle_name': bundle_name,
        'ability_name': final_ability or '',
        'module_name': final_module or 'entry',
        'auto_detected': auto_detected,
        'command_success': start_result.get('command_success', False),
        'window_found': start_result.get('window_found', False),
        'window': start_result.get('window'),
    }
    if start_result.get('error'):
        result['error'] = start_result['error']
    return result


def _resolve_ability(hdc, device_id: str, bundle_name: str,
                     ability_name: str, module_name: str, auto_detect: bool):
    """
    解析 Ability 信息
    
    优化的自动检测逻辑：
    1. 优先使用 get_main_ability 获取推荐的主入口
    2. 如果失败，尝试从 abilities 列表中选择第一个 page 类型的可见 Ability
    3. 最后使用默认值 EntryAbility/entry
    
    Args:
        hdc: HdcWrapper 实例
        device_id: 设备ID
        bundle_name: 包名
        ability_name: 指定的 Ability 名称
        module_name: 指定的模块名称
        auto_detect: 是否自动检测
        
    Returns:
        (ability_name, module_name, auto_detected)
    """
    final_ability = ability_name
    final_module = module_name
    auto_detected = False

    if not final_ability and auto_detect:
        logger.debug(f"未指定Ability,尝试自动检测包 {bundle_name} 的主Ability")
        
        # 1. 优先使用 get_main_ability
        result = hdc.get_main_ability(device_id, bundle_name)
        if result['success'] and result.get('ability_name'):
            final_ability = result['ability_name']
            final_module = final_module or result['module_name']
            auto_detected = True
            logger.debug(f"自动检测到主Ability: {final_ability}, module: {final_module}")
        else:
            # 2. 尝试从 abilities 列表中选择备选
            logger.debug(f"get_main_ability 未找到，尝试从 abilities 列表选择")
            pkg_info = hdc.get_package_info(device_id, bundle_name)
            if pkg_info.get('success'):
                abilities = pkg_info.get('abilities', [])
                # 优先选择 page 类型且 visible 的 Ability
                for ability in abilities:
                    if ability.get('type') == 'page' and ability.get('visible', False):
                        final_ability = ability.get('name')
                        final_module = final_module or ability.get('module', 'entry')
                        auto_detected = True
                        logger.debug(f"从abilities列表选择: {final_ability}, module: {final_module}")
                        break
                # 如果没有，选择第一个 page 类型
                if not final_ability:
                    for ability in abilities:
                        if ability.get('type') == 'page':
                            final_ability = ability.get('name')
                            final_module = final_module or ability.get('module', 'entry')
                            auto_detected = True
                            logger.debug(f"选择第一个page类型: {final_ability}, module: {final_module}")
                            break

    # 使用默认值
    return (
        final_ability or "EntryAbility",
        final_module or "entry",
        auto_detected
    )


@mcp_tool(category="build")
@ToolBase.handle_tool_error('UNINSTALL_ERROR', bundle_name='')
@ToolBase.with_device(bundle_name='')
async def uninstall_app(bundle_name: str, device_id: Optional[str] = None) -> UninstallResult:
    """
    卸载应用

    Args:
        bundle_name: 应用包名
        device_id: 设备ID,如果为None则使用第一个设备

    Returns:
        卸载结果
    """
    hdc = get_hdc()
    success = await asyncio.to_thread(hdc.uninstall_app, device_id, bundle_name)

    return {
        'success': success,
        'device_id': device_id,
        'bundle_name': bundle_name
    }
