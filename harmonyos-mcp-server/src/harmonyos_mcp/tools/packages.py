"""
包管理工具

提供应用包列表、Ability 查询等功能。
"""
import asyncio
from typing import Optional
from loguru import logger

from ..container import get_hdc
from ..types import ListPackagesResult, PackageAbilitiesResult, MainAbilityResult
from .base import ToolBase
from .registry import mcp_tool


@mcp_tool(category="packages")
@ToolBase.handle_tool_error('LIST_PACKAGES_ERROR', packages=[], count=0)
@ToolBase.with_device(packages=[], count=0)
async def list_packages(device_id: str = None, keyword: str = None) -> ListPackagesResult:
    """
    列出设备上已安装的应用包

    Args:
        device_id: 设备ID,如果为None则使用第一个设备
        keyword: 可选的关键字过滤,用于搜索包名

    Returns:
        包含已安装包列表的字典

    Example:
        list_packages(keyword="settings")  -> 搜索包含"settings"的包
        list_packages()  -> 列出所有已安装的包
    """
    hdc = get_hdc()
    result = await asyncio.to_thread(hdc.list_packages, device_id, keyword)
    result['device_id'] = device_id
    
    # 确保必需字段存在
    if 'packages' not in result:
        result['packages'] = []
    if 'count' not in result:
        result['count'] = len(result['packages'])
    
    return result


@mcp_tool(category="packages")
@ToolBase.handle_tool_error('GET_ABILITIES_ERROR', bundle_name='', abilities=[], modules=[], main_ability=None, ability_count=0)
@ToolBase.with_device(bundle_name='', abilities=[], modules=[], main_ability=None, ability_count=0)
async def get_package_abilities(bundle_name: str, device_id: str = None) -> PackageAbilitiesResult:
    """
    获取指定包的所有Abilities

    Args:
        bundle_name: 应用包名
        device_id: 设备ID,如果为None则使用第一个设备

    Returns:
        包含Abilities列表的字典,每个Ability包含name、module、type等信息

    Example:
        get_package_abilities("com.huawei.hmos.settings")
    """
    hdc = get_hdc()
    result = await asyncio.to_thread(hdc.get_package_info, device_id, bundle_name)

    if result['success']:
        return {
            'success': True,
            'device_id': device_id,
            'bundle_name': bundle_name,
            'abilities': result.get('abilities', []),
            'modules': result.get('modules', []),
            'main_ability': result.get('main_ability'),
            'ability_count': len(result.get('abilities', []))
        }
    else:
        result['bundle_name'] = bundle_name
        result['device_id'] = device_id
        result.setdefault('abilities', [])
        result.setdefault('modules', [])
        result.setdefault('main_ability', None)
        result.setdefault('ability_count', 0)
        return result


@mcp_tool(category="packages")
@ToolBase.handle_tool_error('GET_MAIN_ABILITY_ERROR', ability_name='', module_name='', bundle_name='')
@ToolBase.with_device(ability_name='', module_name='', bundle_name='')
async def get_main_ability(bundle_name: str, device_id: str = None) -> MainAbilityResult:
    """
    获取指定包的主入口Ability

    Args:
        bundle_name: 应用包名
        device_id: 设备ID,如果为None则使用第一个设备

    Returns:
        包含主Ability信息的字典(ability_name, module_name)

    Example:
        get_main_ability("com.huawei.hmos.settings")
        -> {"ability_name": "MainAbility", "module_name": "entry"}
    """
    hdc = get_hdc()
    result = await asyncio.to_thread(hdc.get_main_ability, device_id, bundle_name)
    result['device_id'] = device_id
    
    # 确保必需字段存在
    result.setdefault('ability_name', '')
    result.setdefault('module_name', '')
    result.setdefault('bundle_name', bundle_name)
    
    return result
