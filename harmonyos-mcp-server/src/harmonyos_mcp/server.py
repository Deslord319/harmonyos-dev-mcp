"""
HarmonyOS MCP Server 主入口
"""
import sys
from pathlib import Path

from fastmcp import FastMCP
from loguru import logger

from .config import Config
from .utils.logger import setup_logger
from .utils.hdc_wrapper import HdcWrapper
from .utils.hvigor_wrapper import HvigorWrapper
from .utils.uitree_parser import UITreeParser
from .utils.ui_operations import UIOperations

# 设置日志
setup_logger()

# 创建MCP服务器
server = FastMCP("harmonyos-tools")

# 全局变量
hdc_wrapper = None


def init_hdc():
    """初始化hdc包装器"""
    global hdc_wrapper
    if hdc_wrapper is None:
        try:
            hdc_wrapper = HdcWrapper()
            logger.info("hdc包装器初始化成功")
        except Exception as e:
            logger.error(f"hdc包装器初始化失败: {e}")
            raise
    return hdc_wrapper


# ============================================================================
# 设备管理工具
# ============================================================================

@server.tool()
def list_devices() -> dict:
    """
    列出所有连接的HarmonyOS设备和模拟器
    
    Returns:
        包含设备列表的字典
    """
    try:
        hdc = init_hdc()
        devices = hdc.list_devices()
        
        return {
            'success': True,
            'devices': devices,
            'count': len(devices)
        }
    except Exception as e:
        logger.error(f"获取设备列表失败: {e}")
        return {
            'success': False,
            'error': str(e),
            'devices': []
        }


@server.tool()
def get_realtime_logs(device_id: str = None, lines: int = 100, bundle_name: str = None,
             tag: str = None, pid: int = None) -> dict:
    """
    获取设备实时日志（hilog 缓存）

    Args:
        device_id: 设备ID,如果为None则使用第一个设备
        lines: 返回的日志行数
        bundle_name: 应用包名,用于过滤指定应用的日志
        tag: 日志标签过滤
        pid: 进程ID过滤

    Returns:
        包含日志内容的字典
    """
    try:
        hdc = init_hdc()

        # 如果没有指定设备,使用第一个设备
        if not device_id:
            devices = hdc.list_devices()
            if not devices:
                return {
                    'success': False,
                    'error': '没有找到连接的设备'
                }
            device_id = devices[0]

        logs = hdc.get_realtime_logs(device_id, lines, tag=tag, bundle_name=bundle_name, pid=pid)

        filter_info = []
        if bundle_name:
            filter_info.append(f"bundle_name={bundle_name}")
        if tag:
            filter_info.append(f"tag={tag}")
        if pid:
            filter_info.append(f"pid={pid}")

        return {
            'success': True,
            'device_id': device_id,
            'filters': ', '.join(filter_info) if filter_info else 'none',
            'logs': logs
        }
    except Exception as e:
        logger.error(f"获取日志失败: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@server.tool()
def hilog_receive(device_id: str = None, local_dir: str = None) -> dict:
    """
    从HarmonyOS设备的 /data/log/hilog 目录中获取所有 hilog 日志文件和 dict 解密文件

    Args:
        device_id: 设备ID，如果为None则使用第一个设备
        local_dir: 本地保存目录，如果为None则使用当前工作目录

    Returns:
        包含获取结果、文件列表和统计信息的字典
    """
    try:
        hdc = init_hdc()

        # 如果没有指定设备,使用第一个设备
        if not device_id:
            devices = hdc.list_devices()
            if not devices:
                return {
                    'success': False,
                    'error': '没有找到连接的设备'
                }
            device_id = devices[0]

        result = hdc.hilog_receive(device_id, local_dir)
        
        # 添加设备ID到结果
        result['device_id'] = device_id
        
        return result
    except Exception as e:
        logger.error(f"获取hilog文件失败: {e}")
        return {
            'success': False,
            'error': str(e)
        }


# ============================================================================
# 三方库鸿蒙化编译工具
# ============================================================================

@server.tool()
def check_wsl() -> dict:
    """
    检查当前系统是否可用 WSL 环境（用于 Windows 下的交叉编译）

    Returns:
        WSL 检查结果
    """
    try:
        hdc = init_hdc()
        result = hdc.check_wsl_available()
        return result
    except Exception as e:
        logger.error(f"WSL 检查失败: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@server.tool()
def check_harmonyos_compiler_tools(tools_dir: str = "./harmonyos_commandline_tools") -> dict:
    """
    检查 HarmonyOS Command Line Tools 是否已安装

    Args:
        tools_dir: 工具目录路径（默认当前目录的 harmonyos_commandline_tools）

    Returns:
        工具检查结果
    """
    try:
        hdc = init_hdc()
        result = hdc.check_harmonyos_compiler_tools(tools_dir)
        return result
    except Exception as e:
        logger.error(f"编译工具检查失败: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@server.tool()
def clone_library(repo_url: str, local_path: str) -> dict:
    """
    拉取三方库代码仓库

    Args:
        repo_url: 库的 git 仓库 URL (支持 https/git 协议)
        local_path: 本地保存路径

    Returns:
        拉取结果
    """
    try:
        hdc = init_hdc()
        result = hdc.clone_library(repo_url, local_path)
        return result
    except Exception as e:
        logger.error(f"拉取三方库失败: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@server.tool()
def analyze_build_system(project_dir: str) -> dict:
    """
    分析三方库项目的构建系统类型

    Args:
        project_dir: 项目目录路径

    Returns:
        检测到的构建系统列表及其标记文件
    """
    try:
        hdc = init_hdc()
        result = hdc.analyze_build_system(project_dir)
        return result
    except Exception as e:
        logger.error(f"构建系统分析失败: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@server.tool()
def compile_library(
    project_dir: str,
    build_system: str,
    tools_dir: str = None,
    output_dir: str = None,
    extra_args: list = None
) -> dict:
    """
    使用鸿蒙工具链编译三方库

    Args:
        project_dir: 项目目录路径
        build_system: 构建系统类型 (cmake/makefile/autotools/gn)
        tools_dir: HarmonyOS CommandLine Tools 目录路径（可选）
        output_dir: 编译输出目录（可选）
        extra_args: 额外的编译参数列表（可选）

    Returns:
        编译结果，包含成功状态、输出目录和生成的.so文件列表
    """
    try:
        hdc = init_hdc()
        result = hdc.compile_library(
            project_dir=project_dir,
            build_system=build_system,
            tools_dir=tools_dir,
            output_dir=output_dir,
            extra_args=extra_args or []
        )
        return result
    except Exception as e:
        logger.error(f"编译三方库失败: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@server.tool()
def verify_so_output(project_dir: str, output_dir: str = None) -> dict:
    """
    验证编译输出的 .so 文件

    Args:
        project_dir: 项目目录路径
        output_dir: 输出目录（可选，默认为 project_dir/build_harmonyos）

    Returns:
        验证结果，包含文件检查、格式验证等信息
    """
    try:
        hdc = init_hdc()
        result = hdc.verify_so_output(
            project_dir=project_dir,
            output_dir=output_dir
        )
        return result
    except Exception as e:
        logger.error(f"验证.so文件失败: {e}")
        return {
            'success': False,
            'error': str(e)
        }


# ============================================================================
# 构建工具
# ============================================================================

@server.tool()
def build_app(project_path: str, build_mode: str = "debug") -> dict:
    """
    构建HarmonyOS应用

    Args:
        project_path: 项目路径
        build_mode: 构建模式 (debug/release)

    Returns:
        构建结果
    """
    import time
    import datetime

    # 立即写入调试文件，确保我们知道函数被调用了
    debug_file = Path(__file__).parent.parent / "logs" / "build_app_debug.txt"
    debug_file.parent.mkdir(exist_ok=True)

    def debug_log(msg):
        with open(debug_file, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now()}] {msg}\n")
            f.flush()

    debug_log("="*60)
    debug_log(f"build_app 被调用")
    debug_log(f"project_path: {project_path}")
    debug_log(f"build_mode: {build_mode}")

    start_time = time.time()

    try:
        debug_log("步骤1: 创建HvigorWrapper")
        hvigor = HvigorWrapper(project_path)

        debug_log("步骤2: 调用build_hap")
        result = hvigor.build_hap(build_mode=build_mode)

        debug_log(f"步骤3: 构建完成，success={result['success']}")

        elapsed = time.time() - start_time

        response = {
            'success': result['success'],
            'hap_path': result.get('hap_path'),
            'message': f"构建{'成功' if result['success'] else '失败'}，耗时: {elapsed:.2f}秒"
        }

        # 如果构建失败，尝试从日志文件读取错误信息
        if not result['success']:
            try:
                log_file = Path(project_path) / '.hvigor' / 'outputs' / 'build-logs' / 'build.log'
                if log_file.exists():
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        # 查找错误信息（包含 ERROR 的行）
                        error_lines = [line.strip() for line in lines if 'ERROR' in line or 'Error Message' in line]
                        if error_lines:
                            # 只取最后3条错误信息
                            response['error'] = '\n'.join(error_lines[-3:])
            except Exception as e:
                debug_log(f"读取日志文件失败: {e}")

        debug_log(f"步骤4: 即将返回")
        return response
    except Exception as e:
        elapsed = time.time() - start_time
        debug_log(f"异常: {e}")
        return {
            'success': False,
            'error': str(e)
        }


# ============================================================================
# 应用部署工具
# ============================================================================

@server.tool()
def install_app(hap_path: str, device_id: str = None) -> dict:
    """
    安装应用到设备
    
    Args:
        hap_path: HAP包路径
        device_id: 设备ID,如果为None则使用第一个设备
    
    Returns:
        安装结果
    """
    try:
        hdc = init_hdc()
        
        # 如果没有指定设备,使用第一个设备
        if not device_id:
            devices = hdc.list_devices()
            if not devices:
                return {
                    'success': False,
                    'error': '没有找到连接的设备'
                }
            device_id = devices[0]
        
        success = hdc.install_app(device_id, hap_path)
        
        return {
            'success': success,
            'device_id': device_id,
            'hap_path': hap_path
        }
    except Exception as e:
        logger.error(f"安装应用失败: {e}")
        return {
            'success': False,
            'error': str(e)
        }



@server.tool()
def run_app(bundle_name: str, device_id: str = None, ability_name: str = None, module_name: str = None, auto_detect: bool = True) -> dict:
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
    try:
        hdc = init_hdc()

        # 如果没有指定设备,使用第一个设备
        if not device_id:
            devices = hdc.list_devices()
            if not devices:
                return {
                    'success': False,
                    'error': '没有找到连接的设备'
                }
            device_id = devices[0]

        # 如果没有指定ability_name，尝试自动检测
        final_ability_name = ability_name
        final_module_name = module_name
        auto_detected = False
        
        if not final_ability_name and auto_detect:
            logger.info(f"未指定Ability,尝试自动检测包 {bundle_name} 的主Ability")
            main_ability_result = hdc.get_main_ability(device_id, bundle_name)
            
            if main_ability_result['success']:
                final_ability_name = main_ability_result['ability_name']
                final_module_name = final_module_name or main_ability_result['module_name']
                auto_detected = True
                logger.info(f"自动检测到主Ability: {final_ability_name}, module: {final_module_name}")
            else:
                # 自动检测失败，使用默认值
                logger.warning(f"自动检测主Ability失败: {main_ability_result.get('error')}")
                final_ability_name = "EntryAbility"
                final_module_name = final_module_name or "entry"
        
        # 使用默认值
        if not final_ability_name:
            final_ability_name = "EntryAbility"
        if not final_module_name:
            final_module_name = "entry"

        start_result = hdc.start_app(device_id, bundle_name, final_ability_name, final_module_name)

        return {
            'success': start_result['success'],
            'device_id': device_id,
            'bundle_name': bundle_name,
            'ability_name': final_ability_name,
            'module_name': final_module_name,
            'auto_detected': auto_detected,
            'command_success': start_result.get('command_success', False),
            'window_found': start_result.get('window_found', False),
            'window': start_result.get('window'),
            'error': start_result.get('error')
        }
    except Exception as e:
        logger.error(f"运行应用失败: {e}")
        return {
            'success': False,
            'error': str(e)
        }


# ============================================================================
# 包管理工具
# ============================================================================

@server.tool()
def list_packages(device_id: str = None, keyword: str = None) -> dict:
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
        hdc = init_hdc()
        
        # 如果没有指定设备,使用第一个设备
        if not device_id:
            devices = hdc.list_devices()
            if not devices:
                return {
                    'success': False,
                    'error': '没有找到连接的设备'
                }
            device_id = devices[0]
        
        result = hdc.list_packages(device_id, keyword)
        result['device_id'] = device_id
        return result
        
    except Exception as e:
        logger.error(f"获取包列表失败: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@server.tool()
def get_package_abilities(bundle_name: str, device_id: str = None) -> dict:
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
        hdc = init_hdc()
        
        # 如果没有指定设备,使用第一个设备
        if not device_id:
            devices = hdc.list_devices()
            if not devices:
                return {
                    'success': False,
                    'error': '没有找到连接的设备'
                }
            device_id = devices[0]
        
        result = hdc.get_package_info(device_id, bundle_name)
        
        if result['success']:
            # 只返回关键信息，不返回raw_output
            return {
                'success': True,
                'device_id': device_id,
                'bundle_name': bundle_name,
                'abilities': result['abilities'],
                'modules': result['modules'],
                'main_ability': result['main_ability'],
                'ability_count': len(result['abilities'])
            }
        else:
            return result
        
    except Exception as e:
        logger.error(f"获取包Abilities失败: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@server.tool()
def get_main_ability(bundle_name: str, device_id: str = None) -> dict:
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
        hdc = init_hdc()
        
        # 如果没有指定设备,使用第一个设备
        if not device_id:
            devices = hdc.list_devices()
            if not devices:
                return {
                    'success': False,
                    'error': '没有找到连接的设备'
                }
            device_id = devices[0]
        
        result = hdc.get_main_ability(device_id, bundle_name)
        result['device_id'] = device_id
        return result
        
    except Exception as e:
        logger.error(f"获取主Ability失败: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@server.tool()
def uninstall_app(bundle_name: str, device_id: str = None) -> dict:
    """
    卸载应用

    Args:
        bundle_name: 应用包名
        device_id: 设备ID,如果为None则使用第一个设备

    Returns:
        卸载结果
    """
    try:
        hdc = init_hdc()

        # 如果没有指定设备,使用第一个设备
        if not device_id:
            devices = hdc.list_devices()
            if not devices:
                return {
                    'success': False,
                    'error': '没有找到连接的设备'
                }
            device_id = devices[0]

        success = hdc.uninstall_app(device_id, bundle_name)

        return {
            'success': success,
            'device_id': device_id,
            'bundle_name': bundle_name
        }
    except Exception as e:
        logger.error(f"卸载应用失败: {e}")
        return {
            'success': False,
            'error': str(e)
        }


# ============================================================================
# UI树获取工具
# ============================================================================

@server.tool()
def get_ui_tree(device_id: str = None, bundle_name: str = None, window_id: int = None) -> dict:
    """
    获取应用的UI组件树

    Args:
        device_id: 设备ID，如果为None则使用第一个设备
        bundle_name: 应用包名（可选，用于自动查找窗口）
        window_id: 窗口ID（可选，如果指定则直接使用该窗口）

    Returns:
        UI组件树JSON结构
    """
    try:
        hdc = init_hdc()

        # 如果没有指定设备，使用第一个设备
        if not device_id:
            devices = hdc.list_devices()
            if not devices:
                return {
                    'success': False,
                    'error': '没有找到连接的设备'
                }
            device_id = devices[0]

        # 确定窗口ID
        target_window_id = window_id

        if not target_window_id:
            if bundle_name:
                # 根据包名查找窗口
                target_window_id = hdc.find_window_by_bundle(device_id, bundle_name)
                if not target_window_id:
                    return {
                        'success': False,
                        'error': f'未找到应用 {bundle_name} 的窗口'
                    }
            else:
                # 获取窗口列表，使用第一个可见窗口
                window_list = hdc.get_window_list(device_id)
                if not window_list['success'] or not window_list['windows']:
                    return {
                        'success': False,
                        'error': '未找到任何窗口'
                    }

                # 查找第一个可见窗口
                for window in window_list['windows']:
                    if window['is_visible']:
                        target_window_id = window['window_id']
                        break

                if not target_window_id:
                    # 如果没有可见窗口，使用第一个窗口
                    target_window_id = window_list['windows'][0]['window_id']

        # 获取UI树原始数据
        ui_tree_result = hdc.get_ui_tree_raw(device_id, target_window_id)

        if not ui_tree_result['success']:
            return {
                'success': False,
                'error': ui_tree_result.get('error', '获取UI树失败')
            }

        # 解析UI树
        parser = UITreeParser()
        parsed_tree = parser.parse(ui_tree_result['ui_tree'])

        return {
            'success': True,
            'device_id': device_id,
            'window_id': target_window_id,
            'ui_tree': parsed_tree,
            'node_count': parsed_tree['count']
        }

    except Exception as e:
        logger.error(f"获取UI树失败: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@server.tool()
def list_windows(device_id: str = None) -> dict:
    """
    列出设备上的所有窗口

    Args:
        device_id: 设备ID，如果为None则使用第一个设备

    Returns:
        窗口列表
    """
    try:
        hdc = init_hdc()

        # 如果没有指定设备，使用第一个设备
        if not device_id:
            devices = hdc.list_devices()
            if not devices:
                return {
                    'success': False,
                    'error': '没有找到连接的设备'
                }
            device_id = devices[0]

        # 获取窗口列表
        result = hdc.get_window_list(device_id)

        return result

    except Exception as e:
        logger.error(f"获取窗口列表失败: {e}")
        return {
            'success': False,
            'error': str(e)
        }


# ============================================================================
# UI操作工具
# ============================================================================

def init_ui_operations():
    """初始化UI操作工具"""
    hdc = init_hdc()
    return UIOperations(hdc)


@server.tool()
def click_element(device_id: str = None, x: int = None, y: int = None,
                  text: str = None, element_type: str = None,
                  double_click: bool = False, bundle_name: str = None) -> dict:
    """
    点击屏幕上的元素

    Args:
        device_id: 设备ID，如果为None则使用第一个设备
        x: X坐标（与text/element_type二选一）
        y: Y坐标（与text/element_type二选一）
        text: 元素文本（自动查找元素并点击）
        element_type: 元素类型（如Button、Text等）
        double_click: 是否双击
        bundle_name: 应用包名（用于定位窗口，提高查找准确性）

    Returns:
        操作结果
    """
    try:
        hdc = init_hdc()
        ui_ops = UIOperations(hdc)

        # 如果没有指定设备，使用第一个设备
        if not device_id:
            devices = hdc.list_devices()
            if not devices:
                return {'success': False, 'error': '没有找到连接的设备'}
            device_id = devices[0]

        # 如果提供了坐标，直接点击
        if x is not None and y is not None:
            if double_click:
                return ui_ops.double_click(device_id, x, y)
            else:
                return ui_ops.click(device_id, x, y)

        # 如果提供了text或element_type，先查找元素
        if text or element_type:
            result = ui_ops.find_element(device_id, text=text, element_type=element_type, bundle_name=bundle_name)
            if not result['success']:
                return result
            if not result['elements']:
                return {
                    'success': False,
                    'error': f'未找到匹配的元素: text={text}, type={element_type}'
                }

            # 使用第一个匹配的元素
            element = result['elements'][0]
            if 'x' not in element or 'y' not in element:
                return {
                    'success': False,
                    'error': f'元素没有有效的坐标信息: {element}'
                }

            if double_click:
                return ui_ops.double_click(device_id, element['x'], element['y'])
            else:
                return ui_ops.click(device_id, element['x'], element['y'])

        return {
            'success': False,
            'error': '必须提供坐标(x, y)或查找条件(text/element_type)'
        }

    except Exception as e:
        logger.error(f"点击元素失败: {e}")
        return {'success': False, 'error': str(e)}


@server.tool()
def long_press_element(device_id: str = None, x: int = None, y: int = None,
                       text: str = None, element_type: str = None,
                       bundle_name: str = None) -> dict:
    """
    长按屏幕上的元素

    Args:
        device_id: 设备ID，如果为None则使用第一个设备
        x: X坐标
        y: Y坐标
        text: 元素文本（自动查找元素并长按）
        element_type: 元素类型
        bundle_name: 应用包名（用于定位窗口）

    Returns:
        操作结果
    """
    try:
        hdc = init_hdc()
        ui_ops = UIOperations(hdc)

        if not device_id:
            devices = hdc.list_devices()
            if not devices:
                return {'success': False, 'error': '没有找到连接的设备'}
            device_id = devices[0]

        # 如果提供了坐标，直接长按
        if x is not None and y is not None:
            return ui_ops.long_click(device_id, x, y)

        # 查找元素
        if text or element_type:
            result = ui_ops.find_element(device_id, text=text, element_type=element_type, bundle_name=bundle_name)
            if not result['success']:
                return result
            if not result['elements']:
                return {'success': False, 'error': f'未找到匹配的元素'}

            element = result['elements'][0]
            if 'x' not in element or 'y' not in element:
                return {'success': False, 'error': '元素没有有效的坐标信息'}

            return ui_ops.long_click(device_id, element['x'], element['y'])

        return {'success': False, 'error': '必须提供坐标或查找条件'}

    except Exception as e:
        logger.error(f"长按元素失败: {e}")
        return {'success': False, 'error': str(e)}


@server.tool()
def swipe(device_id: str = None, from_x: int = None, from_y: int = None,
          to_x: int = None, to_y: int = None, direction: str = None,
          speed: int = 600) -> dict:
    """
    滑动操作

    Args:
        device_id: 设备ID，如果为None则使用第一个设备
        from_x: 起点X坐标（与direction二选一）
        from_y: 起点Y坐标
        to_x: 终点X坐标
        to_y: 终点Y坐标
        direction: 滑动方向 (left/right/up/down)，与坐标二选一
        speed: 滑动速度 (200-40000, 默认600)

    Returns:
        操作结果
    """
    try:
        hdc = init_hdc()
        ui_ops = UIOperations(hdc)

        if not device_id:
            devices = hdc.list_devices()
            if not devices:
                return {'success': False, 'error': '没有找到连接的设备'}
            device_id = devices[0]

        # 如果提供了方向，使用方向滑动
        if direction:
            return ui_ops.swipe_direction(device_id, direction, speed)

        # 如果提供了坐标，使用坐标滑动
        if all(v is not None for v in [from_x, from_y, to_x, to_y]):
            return ui_ops.swipe(device_id, from_x, from_y, to_x, to_y, speed)

        return {
            'success': False,
            'error': '必须提供滑动坐标(from_x, from_y, to_x, to_y)或方向(direction)'
        }

    except Exception as e:
        logger.error(f"滑动失败: {e}")
        return {'success': False, 'error': str(e)}


@server.tool()
def input_text(device_id: str = None, x: int = None, y: int = None,
               text: str = None, element_text: str = None,
               element_type: str = None, bundle_name: str = None) -> dict:
    """
    在输入框中输入文本

    Args:
        device_id: 设备ID，如果为None则使用第一个设备
        x: 输入框X坐标
        y: 输入框Y坐标
        text: 要输入的文本内容
        element_text: 输入框元素的文本（用于自动查找）
        element_type: 输入框元素类型（如TextInput）
        bundle_name: 应用包名（用于定位窗口）

    Returns:
        操作结果
    """
    try:
        hdc = init_hdc()
        ui_ops = UIOperations(hdc)

        if not device_id:
            devices = hdc.list_devices()
            if not devices:
                return {'success': False, 'error': '没有找到连接的设备'}
            device_id = devices[0]

        if not text:
            return {'success': False, 'error': '必须提供要输入的文本(text)'}

        # 如果提供了坐标，直接输入
        if x is not None and y is not None:
            return ui_ops.input_text(device_id, x, y, text)

        # 查找元素
        if element_text or element_type:
            result = ui_ops.find_element(device_id, text=element_text, element_type=element_type, bundle_name=bundle_name)
            if not result['success']:
                return result
            if not result['elements']:
                return {'success': False, 'error': '未找到匹配的输入框'}

            element = result['elements'][0]
            if 'x' not in element or 'y' not in element:
                return {'success': False, 'error': '元素没有有效的坐标信息'}

            return ui_ops.input_text(device_id, element['x'], element['y'], text)

        return {'success': False, 'error': '必须提供坐标或查找条件'}

    except Exception as e:
        logger.error(f"输入文本失败: {e}")
        return {'success': False, 'error': str(e)}


@server.tool()
def press_key(device_id: str = None, key: str = None) -> dict:
    """
    模拟按键操作

    Args:
        device_id: 设备ID，如果为None则使用第一个设备
        key: 按键名称 (Home/Back/Enter等)

    Returns:
        操作结果
    """
    try:
        hdc = init_hdc()
        ui_ops = UIOperations(hdc)

        if not device_id:
            devices = hdc.list_devices()
            if not devices:
                return {'success': False, 'error': '没有找到连接的设备'}
            device_id = devices[0]

        if not key:
            return {'success': False, 'error': '必须提供按键名称(key)'}

        return ui_ops.press_key(device_id, key)

    except Exception as e:
        logger.error(f"按键操作失败: {e}")
        return {'success': False, 'error': str(e)}


@server.tool()
def find_element(device_id: str = None, text: str = None,
                 element_type: str = None, element_id: str = None,
                 bundle_name: str = None) -> dict:
    """
    在UI树中查找元素

    Args:
        device_id: 设备ID，如果为None则使用第一个设备
        text: 元素文本（模糊匹配）
        element_type: 元素类型（如Button、Text、Image等）
        element_id: 元素ID
        bundle_name: 应用包名（用于定位窗口）

    Returns:
        匹配的元素列表，包含坐标信息
    """
    try:
        hdc = init_hdc()
        ui_ops = UIOperations(hdc)

        if not device_id:
            devices = hdc.list_devices()
            if not devices:
                return {'success': False, 'error': '没有找到连接的设备'}
            device_id = devices[0]

        if not any([text, element_type, element_id]):
            return {
                'success': False,
                'error': '必须提供至少一个查找条件(text/element_type/element_id)'
            }

        return ui_ops.find_element(
            device_id,
            text=text,
            element_type=element_type,
            element_id=element_id,
            bundle_name=bundle_name
        )

    except Exception as e:
        logger.error(f"查找元素失败: {e}")
        return {'success': False, 'error': str(e)}


# 导出 mcp 实例供 FastMCP 使用
mcp = server


def main():
    """MCP 服务器入口函数"""
    # 验证配置
    if not Config.validate():
        logger.error("配置验证失败,请检查环境变量")
        sys.exit(1)

    logger.info("HarmonyOS MCP Server 启动")
    logger.info(f"hdc路径: {Config.HDC_PATH}")

    # 启动MCP服务器
    server.run()


if __name__ == "__main__":
    main()

