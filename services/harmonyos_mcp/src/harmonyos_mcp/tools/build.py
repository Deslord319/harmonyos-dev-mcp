"""
构建部署工具

提供应用构建、安装、运行、卸载等功能。
"""
import asyncio
import re
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from loguru import logger

from ..container import get_hdc
from ..utils.wrappers.hvigor_wrapper import HvigorWrapper
from ..types import BuildResult, InstallResult, RunAppResult, UninstallResult
from .device_base import ToolBase
from common.tools.registry import mcp_tool

# 错误提取配置
MAX_ERRORS = 15  # 最大返回错误数量
ERROR_CONTEXT_LINES = 1  # 每个错误前后额外上下文行数


@mcp_tool(category="build")
@ToolBase.handle_tool_error('BUILD_ERROR', hap_path=None, duration=0)
async def build_app(project_path: str, build_mode: str = "debug") -> BuildResult:
    """构建HarmonyOS应用，生成HAP包。project_path: 项目路径，build_mode: debug/release。"""
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
        errors = _extract_build_errors(project_path, result)
        if errors:
            response['errors'] = errors[:MAX_ERRORS]
            response['error_count'] = len(errors)
            # 提供简短的摘要
            response['error'] = _summarize_errors(errors)

    return response


def _extract_build_errors(project_path: str, build_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    从多个来源提取结构化的错误信息

    Args:
        project_path: 项目路径
        build_result: hvigorw 构建结果（包含 stdout, stderr）

    Returns:
        结构化错误列表，每项包含 file, line, column, message, type
    """
    all_errors = []
    seen_errors = set()  # 用于去重

    # 1. 从 stdout 提取错误
    stdout = build_result.get('stdout', '')
    if stdout:
        for error in _parse_errors_from_text(stdout, 'stdout'):
            error_key = (error.get('file', ''), error.get('line', 0), error.get('message', '')[:50])
            if error_key not in seen_errors:
                seen_errors.add(error_key)
                all_errors.append(error)

    # 2. 从 stderr 提取错误
    stderr = build_result.get('stderr', '')
    if stderr:
        for error in _parse_errors_from_text(stderr, 'stderr'):
            error_key = (error.get('file', ''), error.get('line', 0), error.get('message', '')[:50])
            if error_key not in seen_errors:
                seen_errors.add(error_key)
                all_errors.append(error)

    # 3. 从构建日志提取错误
    log_errors = _extract_errors_from_build_log(project_path)
    for error in log_errors:
        error_key = (error.get('file', ''), error.get('line', 0), error.get('message', '')[:50])
        if error_key not in seen_errors:
            seen_errors.add(error_key)
            all_errors.append(error)

    return all_errors


def _parse_errors_from_text(text: str, source: str) -> List[Dict[str, Any]]:
    """
    从文本中解析结构化错误信息

    支持多种格式：
    - TypeScript: src/main/ets/pages/Index.ets(10,5): error TS2304: Cannot find name 'foo'.
    - ArkTS: ArkTS:ERROR File: src/main/ets/pages/Index.ets:10:5
    - 通用: ERROR: src/main/ets/pages/Index.ets:10:5 - Error message
    - Gradle风格: * What went wrong: ... followed by error details
    """
    errors = []
    lines = text.split('\n')

    # 错误模式匹配
    patterns = [
        # TypeScript/ArkTS 格式: file(line,col): error CODE: message
        re.compile(r'^(.+?\.(?:ts|ets|js))\((\d+),(\d+)\):\s*(?:error|ERROR)\s*(?:\w+)?\s*:\s*(.+)$'),
        # ArkTS 格式: ArkTS:ERROR File: path:line:column
        re.compile(r'^ArkTS:ERROR\s+File:\s*(.+?\.(?:ts|ets|js)):(\d+):(\d+)\s*[-:]?\s*(.*)$'),
        # 通用格式: ERROR: path:line:column - message 或 Error: path:line:column: message
        re.compile(r'^(?:ERROR|Error)\s*[:：]?\s*(.+?\.(?:ts|ets|js|json5?)):(\d+)(?::(\d+))?\s*[-:]?\s*(.+)$'),
        # 编译错误: file:line: error: message
        re.compile(r'^(.+?\.(?:ts|ets|js)):(\d+):\d+:\s*(?:error|ERROR)\s*:\s*(.+)$'),
    ]

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        # 尝试匹配各种格式
        for pattern in patterns:
            match = pattern.match(line)
            if match:
                groups = match.groups()
                # 根据匹配组数确定字段
                if len(groups) == 4:
                    file_path, line_num, col, message = groups
                elif len(groups) == 3:
                    file_path, line_num, message = groups
                    col = '1'
                else:
                    continue

                error = {
                    'file': _normalize_path(file_path.strip()),
                    'line': int(line_num) if line_num else 0,
                    'column': int(col) if col else 0,
                    'message': message.strip() if message else '',
                    'type': _classify_error(message.strip() if message else ''),
                    'source': source
                }
                errors.append(error)
                break

        # 捕获没有文件位置的严重错误
        if not any(p.match(line) for p in patterns):
            if any(kw in line.upper() for kw in ['FATAL', 'FAILED', 'BUILD FAILED', 'COMPILATION FAILED']):
                # 提取有意义的错误消息
                clean_msg = re.sub(r'^\s*[-*]\s*', '', line).strip()
                if clean_msg and len(clean_msg) > 5:
                    errors.append({
                        'file': None,
                        'line': 0,
                        'column': 0,
                        'message': clean_msg,
                        'type': 'build',
                        'source': source
                    })

    return errors


def _extract_errors_from_build_log(project_path: str) -> List[Dict[str, Any]]:
    """
    从构建日志文件提取错误信息
    """
    errors = []
    try:
        log_file = Path(project_path) / '.hvigor' / 'outputs' / 'build-logs' / 'build.log'
        if not log_file.exists():
            return errors

        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        errors = _parse_errors_from_text(content, 'build.log')
    except Exception as e:
        logger.debug(f"读取构建日志失败: {e}")

    return errors


def _normalize_path(path: str) -> str:
    """标准化文件路径，使其相对于项目根目录"""
    # 移除常见的路径前缀
    prefixes = ['/entry/', '/build/', '/src/', '\\entry\\', '\\build\\', '\\src\\']
    for prefix in prefixes:
        if prefix in path or prefix.replace('/', '\\') in path:
            idx = max(path.find(prefix), path.find(prefix.replace('/', '\\')))
            if idx >= 0:
                return path[idx + 1:]

    # 如果是绝对路径，尝试提取相对部分
    if path.startswith('/') or ':' in path[:3]:
        parts = path.replace('\\', '/').split('/')
        for i, part in enumerate(parts):
            if part in ['src', 'entry', 'build']:
                return '/'.join(parts[i:])

    return path


def _classify_error(message: str) -> str:
    """根据错误消息分类错误类型"""
    message_lower = message.lower()

    if any(kw in message_lower for kw in ['cannot find', 'not found', 'no such', 'does not exist']):
        return 'missing'
    elif any(kw in message_lower for kw in ['type', 'cannot be assigned', 'is not compatible']):
        return 'type'
    elif any(kw in message_lower for kw in ['syntax', 'unexpected', 'expected']):
        return 'syntax'
    elif any(kw in message_lower for kw in ['import', 'export', 'module']):
        return 'module'
    elif any(kw in message_lower for kw in ['permission', 'denied', 'access']):
        return 'permission'
    elif any(kw in message_lower for kw in ['config', 'profile', 'json', 'schema']):
        return 'config'
    else:
        return 'compile'


def _summarize_errors(errors: List[Dict[str, Any]]) -> str:
    """生成错误摘要"""
    if not errors:
        return ''

    # 按类型分组
    type_counts = {}
    for e in errors:
        t = e.get('type', 'unknown')
        type_counts[t] = type_counts.get(t, 0) + 1

    # 生成摘要
    parts = []
    if type_counts.get('type'):
        parts.append(f"{type_counts['type']}个类型错误")
    if type_counts.get('syntax'):
        parts.append(f"{type_counts['syntax']}个语法错误")
    if type_counts.get('missing'):
        parts.append(f"{type_counts['missing']}个缺失引用")
    if type_counts.get('module'):
        parts.append(f"{type_counts['module']}个模块错误")

    other = sum(v for k, v in type_counts.items() if k not in ['type', 'syntax', 'missing', 'module'])
    if other:
        parts.append(f"{other}个其他错误")

    summary = f"构建失败，共{len(errors)}个错误"
    if parts:
        summary += f"：{', '.join(parts)}"

    return summary


@mcp_tool(category="build")
@ToolBase.handle_tool_error('INSTALL_ERROR', hap_path='')
@ToolBase.with_device(hap_path='')
async def install_app(hap_path: str, device_id: Optional[str] = None) -> InstallResult:
    """安装HAP包到设备。hap_path: HAP包路径，device_id: 设备ID（可选）。"""
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
    """启动应用。bundle_name: 包名，ability_name/module_name: 入口（可选，默认自动检测）。"""
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
    """卸载应用。bundle_name: 应用包名，device_id: 设备ID（可选）。"""
    hdc = get_hdc()
    success = await asyncio.to_thread(hdc.uninstall_app, device_id, bundle_name)

    return {
        'success': success,
        'device_id': device_id,
        'bundle_name': bundle_name
    }
