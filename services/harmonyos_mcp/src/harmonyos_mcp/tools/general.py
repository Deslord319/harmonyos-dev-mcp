"""
通用工具

提供设备管理、包管理等基础功能。
"""
import asyncio
from typing import Optional, Literal
from loguru import logger

from ..container import get_hdc
from ..types import ListDevicesResult, QueryPackageResult
from .device_base import ToolBase
from common.tools.registry import mcp_tool


@mcp_tool(category="general")
@ToolBase.handle_tool_error('DEVICE_LIST_ERROR', devices=[], count=0)
async def list_devices() -> ListDevicesResult:
    """
    列出所有连接的HarmonyOS设备和模拟器
    
    默认返回设备详细信息（型号、系统版本、屏幕分辨率等）。
    
    Returns:
        包含设备列表的字典:
        - success: 是否成功
        - devices: 设备信息列表，每个设备包含:
            - device_id: 设备ID
            - model: 设备型号
            - brand: 品牌
            - os_version: 系统版本
            - api_version: API版本
            - screen_size: 屏幕分辨率
        - count: 设备数量
    """
    hdc = get_hdc()
    devices = await asyncio.to_thread(hdc.list_devices_with_info)
    
    return {
        'success': True,
        'devices': devices,
        'count': len(devices)
    }


# query_package 按 info_type 的错误默认字段
_LIST_ERROR_DEFAULTS = {'packages': [], 'count': 0}
_ABILITIES_ERROR_DEFAULTS = {'abilities': [], 'modules': [], 'main_ability': None, 'ability_count': 0}
_MAIN_ABILITY_ERROR_DEFAULTS = {'ability_name': '', 'module_name': ''}
_PERMISSIONS_ERROR_DEFAULTS = {'requested_permissions': [], 'permission_count': 0}


@mcp_tool(category="general")
@ToolBase.handle_tool_error('QUERY_PACKAGE_ERROR', info_type='list', **_LIST_ERROR_DEFAULTS)
@ToolBase.with_device(info_type='list', **_LIST_ERROR_DEFAULTS)
async def query_package(
    device_id: Optional[str] = None,
    bundle_name: Optional[str] = None,
    keyword: Optional[str] = None,
    info_type: Literal['list', 'abilities', 'main_ability', 'permissions'] = 'list'
) -> QueryPackageResult:
    """
    统一的包查询工具（合并 list_packages、get_package_abilities、get_main_ability、get_permissions）
    
    根据参数组合执行不同查询：
    - bundle_name 为空: 列出所有包（可用 keyword 过滤）
    - bundle_name 非空 + info_type="abilities": 获取所有 Abilities
    - bundle_name 非空 + info_type="main_ability": 仅获取主 Ability
    - bundle_name 非空 + info_type="permissions": 获取应用权限列表

    Args:
        device_id: 设备ID，如果为None则使用第一个设备
        bundle_name: 应用包名（可选，指定后查询该包的详情）
        keyword: 关键字过滤（仅在 list 模式下生效）
        info_type: 查询类型
            - list: 列出所有包（默认）
            - abilities: 获取指定包的所有 Abilities
            - main_ability: 获取指定包的主入口 Ability
            - permissions: 获取指定包的权限列表

    Returns:
        根据 info_type 返回不同结构的结果字典

    Example:
        # 列出所有包
        query_package()
        
        # 搜索包含 "settings" 的包
        query_package(keyword="settings")
        
        # 获取指定包的所有 Abilities
        query_package(bundle_name="com.huawei.hmos.settings", info_type="abilities")
        
        # 获取指定包的主 Ability
        query_package(bundle_name="com.huawei.hmos.settings", info_type="main_ability")
        
        # 获取指定包的权限列表
        query_package(bundle_name="com.huawei.hmos.settings", info_type="permissions")
    """
    hdc = get_hdc()
    
    # 参数校验：需要 bundle_name 的查询类型
    if info_type in ('abilities', 'main_ability', 'permissions') and not bundle_name:
        return {
            'success': False,
            'error': f'info_type="{info_type}" 需要指定 bundle_name 参数',
            'error_code': 'MISSING_BUNDLE_NAME',
            'device_id': device_id,
            'info_type': info_type,
        }
    
    # 如果指定了 bundle_name 但 info_type 是 list，自动切换到 abilities
    if bundle_name and info_type == 'list':
        info_type = 'abilities'
    
    # === list 模式：列出所有包 ===
    if info_type == 'list':
        result = await asyncio.to_thread(hdc.list_packages, device_id, keyword)
        return {
            'success': result.get('success', True),
            'device_id': device_id,
            'info_type': 'list',
            'packages': result.get('packages', []),
            'count': result.get('count', len(result.get('packages', []))),
            'keyword': keyword or ''
        }
    
    # === abilities 模式：获取所有 Abilities ===
    if info_type == 'abilities':
        result = await asyncio.to_thread(hdc.get_package_info, device_id, bundle_name)
        if result.get('success'):
            # 转换 abilities 格式，只保留 AbilityInfo 需要的字段
            raw_abilities = result.get('abilities', [])
            abilities = [
                {'name': a.get('name', ''), 'module': a.get('module', ''), 'type': a.get('type', '')}
                for a in raw_abilities
            ]
            # 转换 modules 格式，从 [{'name': 'entry'}] 转为 ['entry']
            raw_modules = result.get('modules', [])
            modules = [m.get('name', m) if isinstance(m, dict) else m for m in raw_modules]
            # 转换 main_ability 格式
            raw_main = result.get('main_ability')
            main_ability = None
            if raw_main:
                main_ability = {'name': raw_main.get('name', ''), 'module': raw_main.get('module', ''), 'type': raw_main.get('type', '')}
            return {
                'success': True,
                'device_id': device_id,
                'info_type': 'abilities',
                'bundle_name': bundle_name,
                'abilities': abilities,
                'modules': modules,
                'main_ability': main_ability,
                'ability_count': len(abilities)
            }
        else:
            return {
                'success': False,
                'error': result.get('error', '获取 Abilities 失败'),
                'error_code': result.get('error_code', 'GET_ABILITIES_ERROR'),
                'device_id': device_id,
                'info_type': 'abilities',
                'bundle_name': bundle_name,
                **_ABILITIES_ERROR_DEFAULTS
            }
    
    # === main_ability 模式：仅获取主 Ability ===
    if info_type == 'main_ability':
        result = await asyncio.to_thread(hdc.get_main_ability, device_id, bundle_name)
        return {
            'success': result.get('success', False),
            'device_id': device_id,
            'info_type': 'main_ability',
            'bundle_name': bundle_name,
            'ability_name': result.get('ability_name', ''),
            'module_name': result.get('module_name', ''),
            'error': result.get('error') if not result.get('success') else None
        }
    
    # === permissions 模式：获取应用权限列表 ===
    if info_type == 'permissions':
        result = await asyncio.to_thread(hdc.get_package_permissions, device_id, bundle_name)
        return {
            'success': result.get('success', False),
            'device_id': device_id,
            'info_type': 'permissions',
            'bundle_name': bundle_name,
            'requested_permissions': result.get('requested_permissions', []),
            'permission_count': result.get('permission_count', 0),
            'error': result.get('error') if not result.get('success') else None
        }
    
    # 不应到达此处
    return {
        'success': False,
        'error': f'不支持的 info_type: {info_type}',
        'error_code': 'INVALID_INFO_TYPE',
        'device_id': device_id,
        'info_type': info_type
    }
