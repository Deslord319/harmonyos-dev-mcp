"""
包管理工具

提供应用包列表、Ability 查询等功能。
"""
from typing import Optional
from loguru import logger

from ..container import get_hdc
from ..types import ListPackagesResult, PackageAbilitiesResult, MainAbilityResult
from .base import ToolBase


def list_packages(device_id: str = None, keyword: str = None) -> ListPackagesResult:
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
    try:
        ok, device = ToolBase.get_device_id(device_id)
        if not ok:
            return device

        hdc = get_hdc()
        result = hdc.list_packages(device, keyword)
        result['device_id'] = device
        
        return result

    except Exception as e:
        return ToolBase.wrap_error(e, 'LIST_PACKAGES_ERROR')


def get_package_abilities(bundle_name: str, device_id: str = None) -> PackageAbilitiesResult:
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
    try:
        ok, device = ToolBase.get_device_id(device_id)
        if not ok:
            return device

        hdc = get_hdc()
        result = hdc.get_package_info(device, bundle_name)

        if result['success']:
            # 只返回关键信息，不返回raw_output
            return {
                'success': True,
                'device_id': device,
                'bundle_name': bundle_name,
                'abilities': result['abilities'],
                'modules': result['modules'],
                'main_ability': result['main_ability'],
                'ability_count': len(result['abilities'])
            }
        else:
            return result

    except Exception as e:
        return ToolBase.wrap_error(e, 'GET_ABILITIES_ERROR')


def get_main_ability(bundle_name: str, device_id: str = None) -> MainAbilityResult:
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
    try:
        ok, device = ToolBase.get_device_id(device_id)
        if not ok:
            # 确保错误结果也包含必需字段
            device['ability_name'] = ''
            device['module_name'] = ''
            device['bundle_name'] = bundle_name
            return device

        hdc = get_hdc()
        result = hdc.get_main_ability(device, bundle_name)
        result['device_id'] = device
        
        # 确保必需字段存在
        if 'ability_name' not in result:
            result['ability_name'] = ''
        if 'module_name' not in result:
            result['module_name'] = ''
        if 'bundle_name' not in result:
            result['bundle_name'] = bundle_name
        
        return result

    except Exception as e:
        error_result = ToolBase.wrap_error(e, 'GET_MAIN_ABILITY_ERROR')
        error_result['ability_name'] = ''
        error_result['module_name'] = ''
        error_result['bundle_name'] = bundle_name
        return error_result
