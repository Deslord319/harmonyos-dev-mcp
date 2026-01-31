"""
HarmonyOS MCP Server 主入口
"""
import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from fastmcp import FastMCP
from loguru import logger
from config import Config, LogSecurityConfig
from utils.logger import setup_logger
from utils.hdc_wrapper import HdcWrapper, HDCCapabilities
from utils.hvigor_wrapper import HvigorWrapper
from utils.uitree_parser import UITreeParser
from utils.ui_operations import UIOperations
from utils.log_parser import LogParser, LogEntry
from utils.hilogtool_wrapper import HilogtoolWrapper, get_hilogtool_wrapper

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
def run_app(bundle_name: str, device_id: str = None, ability_name: str = "EntryAbility") -> dict:
    """
    运行应用

    Args:
        bundle_name: 应用包名
        device_id: 设备ID,如果为None则使用第一个设备
        ability_name: Ability名称

    Returns:
        运行结果
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

        success = hdc.start_app(device_id, bundle_name, ability_name)

        return {
            'success': success,
            'device_id': device_id,
            'bundle_name': bundle_name,
            'ability_name': ability_name
        }
    except Exception as e:
        logger.error(f"运行应用失败: {e}")
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


# ============================================================================
# 日志分析工具
# ============================================================================

def _logs_fetch_impl(
    device_id: str = None,
    lines: int = 100,
    level: str = None,
    tag: str = None,
    keyword: str = None,
    pid: int = None,
    start_time: str = None,
    end_time: str = None,
    seconds: int = None
) -> dict:
    """
    日志获取的内部实现（供工具函数调用）
    """
    from datetime import datetime, timedelta
    
    try:
        hdc = init_hdc()
        
        # 获取设备
        if not device_id:
            devices = hdc.list_devices()
            if not devices:
                return {'success': False, 'error': '没有找到连接的设备'}
            device_id = devices[0]
        
        # 限制最大行数
        lines = min(lines, LogSecurityConfig.MAX_LOG_LINES)
        
        # 获取日志（获取更多行以便过滤后仍有足够数据）
        fetch_lines = min(lines * 5, LogSecurityConfig.MAX_LOG_LINES)
        log_text = hdc.get_realtime_logs(device_id, lines=fetch_lines, tag=tag, pid=pid)
        
        if not log_text:
            return {
                'success': True,
                'device_id': device_id,
                'logs': [],
                'total_lines': 0,
                'message': '未获取到日志'
            }
        
        # 解析日志
        raw_lines = log_text.split('\n')
        entries = LogParser.parse_logs(raw_lines)
        
        # 构建时间范围
        time_range = None
        if seconds:
            # 最近N秒
            now = datetime.now()
            time_range = {
                'start': (now - timedelta(seconds=seconds)).isoformat(),
                'end': now.isoformat()
            }
        elif start_time or end_time:
            time_range = {}
            today = datetime.now().strftime('%Y-%m-%d')
            
            if start_time:
                # 如果只有时间没有日期，补上今天的日期
                if len(start_time) <= 8:  # HH:MM:SS
                    start_time = f"{today} {start_time}"
                time_range['start'] = start_time
            
            if end_time:
                if len(end_time) <= 8:
                    end_time = f"{today} {end_time}"
                time_range['end'] = end_time
        
        # 应用过滤
        filtered_entries = LogParser.filter_entries(
            entries,
            level=level,
            tag=tag,
            keyword=keyword,
            time_range=time_range,
            pid=pid,
            seconds=seconds
        )
        
        # 限制返回行数
        truncated = len(filtered_entries) > lines
        filtered_entries = filtered_entries[:lines]
        
        # 获取统计
        summary = LogParser.analyze_summary(filtered_entries)
        
        return {
            'success': True,
            'device_id': device_id,
            'logs': [e.raw_line for e in filtered_entries],
            'total_lines': len(filtered_entries),
            'truncated': truncated,
            'filters_applied': {
                'level': level,
                'tag': tag,
                'keyword': keyword,
                'pid': pid,
                'time_range': time_range,
                'seconds': seconds
            },
            'summary': {
                'level_stats': summary.get('level_stats', {}),
                'time_range': summary.get('time_range')
            }
        }
        
    except Exception as e:
        logger.error(f"获取日志失败: {e}")
        return {'success': False, 'error': str(e)}


@server.tool()
def logs_fetch(
    device_id: str = None,
    lines: int = 100,
    level: str = None,
    tag: str = None,
    keyword: str = None,
    pid: int = None,
    start_time: str = None,
    end_time: str = None,
    seconds: int = None
) -> dict:
    """
    从设备获取日志（支持多种过滤条件）
    
    Args:
        device_id: 设备ID，如果为None则使用第一个设备
        lines: 最大返回行数（默认100，最大50000）
        level: 日志级别过滤 (D/I/W/E/F)，会返回该级别及以上
        tag: Tag 过滤（模糊匹配）
        keyword: 关键字过滤（在日志内容中搜索）
        pid: 进程ID过滤
        start_time: 开始时间（格式：HH:MM:SS 或 YYYY-MM-DD HH:MM:SS）
        end_time: 结束时间（格式：HH:MM:SS 或 YYYY-MM-DD HH:MM:SS）
        seconds: 获取最近N秒内的日志（与start_time/end_time互斥）
    
    Returns:
        包含日志内容、过滤信息和统计的字典
    """
    return _logs_fetch_impl(
        device_id=device_id,
        lines=lines,
        level=level,
        tag=tag,
        keyword=keyword,
        pid=pid,
        start_time=start_time,
        end_time=end_time,
        seconds=seconds
    )


@server.tool()
def logs_save_snapshot(
    device_id: str = None,
    output_path: str = None,
    lines: int = 1000,
    level: str = None,
    tag: str = None,
    keyword: str = None,
    seconds: int = None,
    start_time: str = None,
    end_time: str = None,
    include_analysis: bool = True
) -> dict:
    """
    保存日志快照到本地文件（用于审计和复现）
    
    Args:
        device_id: 设备ID，如果为None则使用第一个设备
        output_path: 输出文件路径（默认自动生成，保存在 ./hm_logs/ 目录）
        lines: 最大保存行数（默认1000）
        level: 日志级别过滤
        tag: Tag 过滤
        keyword: 关键字过滤
        seconds: 获取最近N秒内的日志
        start_time: 开始时间
        end_time: 结束时间
        include_analysis: 是否在文件中包含分析摘要
    
    Returns:
        保存结果，包含文件路径和统计信息
    """
    from datetime import datetime
    import os
    
    try:
        # 先获取日志（调用内部实现，避免 FunctionTool 问题）
        fetch_result = _logs_fetch_impl(
            device_id=device_id,
            lines=lines,
            level=level,
            tag=tag,
            keyword=keyword,
            seconds=seconds,
            start_time=start_time,
            end_time=end_time
        )
        
        if not fetch_result['success']:
            return fetch_result
        
        logs = fetch_result.get('logs', [])
        if not logs:
            return {
                'success': False,
                'error': '没有日志可保存'
            }
        
        # 确定输出路径
        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"./hm_logs/hilog_snapshot_{timestamp}.txt"
        
        # 验证路径白名单
        valid, result_path = LogSecurityConfig.validate_save_path(output_path)
        if not valid:
            return {
                'success': False,
                'error': result_path
            }
        
        # 确保目录存在
        output_dir = os.path.dirname(result_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # 写入文件
        with open(result_path, 'w', encoding='utf-8') as f:
            # 写入头部信息
            f.write("=" * 80 + "\n")
            f.write(f"HarmonyOS 日志快照\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"设备ID: {fetch_result.get('device_id', 'N/A')}\n")
            f.write(f"日志行数: {len(logs)}\n")
            
            # 写入过滤条件
            filters = fetch_result.get('filters_applied', {})
            active_filters = {k: v for k, v in filters.items() if v}
            if active_filters:
                f.write(f"过滤条件: {active_filters}\n")
            
            f.write("=" * 80 + "\n\n")
            
            # 写入分析摘要
            if include_analysis:
                summary = fetch_result.get('summary', {})
                if summary:
                    f.write("--- 日志分析摘要 ---\n")
                    level_stats = summary.get('level_stats', {})
                    if level_stats:
                        f.write(f"级别统计: {level_stats}\n")
                    time_range = summary.get('time_range')
                    if time_range:
                        f.write(f"时间范围: {time_range.get('start', 'N/A')} ~ {time_range.get('end', 'N/A')}\n")
                    f.write("\n")
            
            f.write("--- 日志内容 ---\n\n")
            
            # 写入日志内容
            for line in logs:
                f.write(line + "\n")
        
        # 获取文件大小
        file_size = os.path.getsize(result_path)
        
        return {
            'success': True,
            'saved_path': result_path,
            'file_size': file_size,
            'file_size_human': f"{file_size / 1024:.1f} KB" if file_size < 1024 * 1024 else f"{file_size / 1024 / 1024:.1f} MB",
            'log_count': len(logs),
            'device_id': fetch_result.get('device_id'),
            'filters_applied': filters,
            'truncated': fetch_result.get('truncated', False)
        }
        
    except Exception as e:
        logger.error(f"保存日志快照失败: {e}")
        return {'success': False, 'error': str(e)}


@server.tool()
def logs_analyze(
    logs: list = None,
    device_id: str = None,
    analysis_type: str = "summary",
    level: str = None,
    tag: str = None,
    keyword: str = None,
    lines: int = 1000,
    custom_regex: str = None
) -> dict:
    """
    对日志进行结构化分析（基于正则匹配，不依赖LLM）
    
    可以直接传入日志列表，或从设备获取日志后分析。
    
    Args:
        logs: 日志行列表（如果提供则直接分析，否则从设备获取）
        device_id: 设备ID（当 logs 为空时使用）
        analysis_type: 分析类型
            - summary: 摘要统计（级别分布、Top Tags、时间范围）
            - errors: 错误分析（E/F级别日志分组、异常类型识别）
            - performance: 性能分析（提取耗时数据、统计指标）
            - crashes: 崩溃分析（Crash/ANR/Exception 识别）
            - custom: 自定义正则匹配
        level: 日志级别过滤 (D/I/W/E/F)
        tag: Tag 过滤
        keyword: 关键字过滤
        lines: 获取日志行数（当从设备获取时）
        custom_regex: 自定义正则表达式（仅 analysis_type=custom 时使用）
    
    Returns:
        分析结果，包含 success、analysis_type、result 和 evidence_lines
    """
    try:
        # 如果没有提供日志，则从设备获取
        if not logs:
            hdc = init_hdc()
            
            # 获取设备
            if not device_id:
                devices = hdc.list_devices()
                if not devices:
                    return {'success': False, 'error': '没有找到连接的设备'}
                device_id = devices[0]
            
            # 获取日志
            log_text = hdc.get_realtime_logs(device_id, lines=lines, tag=tag)
            if not log_text:
                return {
                    'success': False,
                    'error': '无法获取设备日志'
                }
            logs = log_text.split('\n')
        
        # 解析日志
        entries = LogParser.parse_logs(logs)
        
        # 应用过滤
        if level or tag or keyword:
            entries = LogParser.filter_entries(
                entries,
                level=level,
                tag=tag,
                keyword=keyword
            )
        
        # 执行分析
        result = LogParser.analyze(entries, analysis_type, custom_regex)
        
        # 获取证据行（用于审计）
        evidence_lines = []
        if analysis_type == 'errors':
            # 提取错误日志样本作为证据
            error_entries = [e for e in entries if e.level in ('E', 'F')][:10]
            evidence_lines = [e.raw_line for e in error_entries]
        elif analysis_type == 'crashes':
            # 提取崩溃相关日志作为证据
            for e in entries[:100]:
                if any(p.search(e.raw_line) for p in LogParser.ERROR_PATTERNS.values()):
                    evidence_lines.append(e.raw_line)
                    if len(evidence_lines) >= 10:
                        break
        
        return {
            'success': True,
            'analysis_type': analysis_type,
            'result': result,
            'evidence_lines': evidence_lines,
            'total_entries_analyzed': len(entries),
            'filters_applied': {
                'level': level,
                'tag': tag,
                'keyword': keyword
            }
        }
        
    except Exception as e:
        logger.error(f"日志分析失败: {e}")
        return {'success': False, 'error': str(e)}


@server.tool()
def health_check() -> dict:
    """
    检查 hdc 和 hilogtool 环境状态
    
    检测项目：
    - hdc 是否可用及版本信息
    - 支持的 hdc 子命令
    - hilog 参数支持情况
    - hilogtool 是否可用
    - 当前连接的设备数量
    
    Returns:
        环境检查结果，包含各工具状态和建议
    """
    result = {
        'success': True,
        'hdc': {
            'available': False,
            'version': None,
            'path': Config.HDC_PATH,
            'supported_commands': [],
            'hilog_capabilities': {}
        },
        'hilogtool': {
            'available': False,
            'path': Config.HILOGTOOL_PATH,
            'version': None
        },
        'devices': {
            'count': 0,
            'online': 0,
            'list': []
        },
        'issues': [],
        'suggestions': []
    }
    
    # 检查 hdc
    try:
        hdc = init_hdc()
        
        # 获取版本信息
        version_info = HDCCapabilities.probe_version()
        result['hdc']['available'] = version_info.get('available', False)
        result['hdc']['version'] = version_info.get('version')
        
        if result['hdc']['available']:
            # 获取支持的命令
            commands = HDCCapabilities.probe_supported_commands()
            result['hdc']['supported_commands'] = [cmd for cmd, supported in commands.items() if supported]
            
            # 获取 hilog 能力
            hilog_caps = HDCCapabilities.probe_hilog_support()
            result['hdc']['hilog_capabilities'] = {
                k: v for k, v in hilog_caps.items() 
                if k != 'raw_help' and isinstance(v, bool)
            }
            
            # 获取设备列表
            devices = hdc.list_devices()
            result['devices']['count'] = len(devices)
            result['devices']['online'] = len(devices)
            result['devices']['list'] = devices
            
            if not devices:
                result['issues'].append('未检测到连接的设备')
                result['suggestions'].append('请确保设备已通过 USB 连接并开启 USB 调试')
        else:
            result['issues'].append('hdc 工具不可用')
            result['suggestions'].append('请检查 HDC_PATH 环境变量或安装 DevEco Studio')
            
    except Exception as e:
        result['hdc']['available'] = False
        result['issues'].append(f'hdc 初始化失败: {str(e)}')
        result['suggestions'].append('请检查 hdc 工具路径配置')
    
    # 检查 hilogtool
    try:
        hilogtool = get_hilogtool_wrapper()
        result['hilogtool']['available'] = hilogtool.is_available()
        
        if result['hilogtool']['available']:
            version_result = hilogtool.get_version()
            if version_result['success']:
                result['hilogtool']['version'] = version_result.get('version')
        else:
            result['issues'].append('hilogtool 不可用（用于解析加密的 hilog 文件）')
            result['suggestions'].append('请设置 HILOGTOOL_PATH 环境变量指向 DevEco Studio SDK 中的 hilogtool.exe')
            
    except Exception as e:
        result['hilogtool']['available'] = False
        logger.warning(f"hilogtool 检查失败: {e}")
    
    # 生成总体状态
    if result['hdc']['available'] and result['devices']['count'] > 0:
        result['status'] = 'ready'
        result['message'] = f"环境就绪，检测到 {result['devices']['count']} 个设备"
    elif result['hdc']['available']:
        result['status'] = 'partial'
        result['message'] = "hdc 可用但未检测到设备"
    else:
        result['status'] = 'error'
        result['message'] = "hdc 不可用，请检查配置"
    
    return result


@server.tool()
def logs_parse_hilog_files(
    hilog_dir: str,
    output_dir: str = None,
    dict_path: str = None,
    max_lines: int = 10000
) -> dict:
    """
    解析本地的 hilog 加密日志文件
    
    使用 hilogtool.exe parse 命令解析从设备拉取的加密 hilog 文件
    
    Args:
        hilog_dir: hilog 文件所在目录或单个 .gz 文件路径
        output_dir: 解析后的输出目录（默认 ./hm_logs/parsed）
        dict_path: 字典文件路径（hilog_dict.*.zip），用于解密
        max_lines: 最大读取行数
    
    Returns:
        解析结果，包含解析后的日志内容
    """
    try:
        hilogtool = get_hilogtool_wrapper()
        
        if not hilogtool.is_available():
            return {
                'success': False,
                'error': 'hilogtool 不可用，请检查 HILOGTOOL_PATH 配置'
            }
        
        # 设置默认输出目录
        if not output_dir:
            output_dir = './hm_logs/parsed'
        
        # 验证输出路径
        valid, abs_path = LogSecurityConfig.validate_save_path(output_dir)
        if not valid:
            return {
                'success': False,
                'error': abs_path
            }
        
        # 解析并读取
        result = hilogtool.parse_and_read(
            hilog_dir,
            dict_path=dict_path,
            max_lines=max_lines
        )
        
        return result
        
    except Exception as e:
        logger.error(f"hilog 解析失败: {e}")
        return {'success': False, 'error': str(e)}


if __name__ == "__main__":
    # 验证配置
    if not Config.validate():
        logger.error("配置验证失败,请检查环境变量")
        sys.exit(1)
    
    logger.info("HarmonyOS MCP Server 启动")
    logger.info(f"hdc路径: {Config.HDC_PATH}")
    
    # 启动MCP服务器
    server.run()

