"""
hdc UI 操作模块

提供 UI 树获取、窗口管理等功能。
"""
import re
from typing import Optional, Dict, Any
from loguru import logger

from harmonyos_mcp.config import Config


class HdcUI:
    """UI 操作相关方法"""

    def get_window_list(self, device_id: str) -> Dict[str, Any]:
        """
        获取所有窗口列表

        Args:
            device_id: 设备ID

        Returns:
            包含窗口列表的字典
        """
        logger.info(f"获取设备 {device_id} 的窗口列表")
        command = "hidumper -s WindowManagerService -a '-a'"
        result = self.execute_shell(device_id, command)

        if not result['success']:
            logger.error(f"获取窗口列表失败: {result['stderr']}")
            return {
                'success': False,
                'error': result['stderr'],
                'windows': []
            }

        # 解析窗口列表
        windows = []
        lines = result['stdout'].split('\n')

        # 查找表头行
        header_idx = -1
        for i, line in enumerate(lines):
            if 'WindowName' in line and 'WinId' in line:
                header_idx = i
                break

        if header_idx == -1:
            logger.warning("未找到窗口列表表头")
            return {
                'success': True,
                'windows': [],
                'raw_output': result['stdout']
            }

        # 解析窗口数据
        # 实际格式: WindowName DisplayId Pid WinId Type Mode Flag ZOrd Orientation [ x y w h ] ...
        # 其中 ZOrd > 0 表示窗口可见，ZOrd = -1 表示窗口隐藏
        for line in lines[header_idx + 1:]:
            line = line.strip()
            if not line:
                continue
            # 跳过分隔线
            if line.startswith('-'):
                continue

            # 使用正则提取窗口信息和矩形区域
            # 格式: WindowName DisplayId Pid WinId Type Mode Flag ZOrd Orient [ x y w h ] ...
            match = re.match(
                r'^(\S+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(-?\d+)\s+(\d+)\s+\[\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*\]',
                line
            )
            if match:
                try:
                    zord = int(match.group(8))
                    window_info = {
                        'window_name': match.group(1),
                        'display_id': int(match.group(2)),
                        'pid': int(match.group(3)),
                        'window_id': int(match.group(4)),
                        'type': int(match.group(5)),
                        'mode': int(match.group(6)),
                        'flag': int(match.group(7)),
                        'zord': zord,
                        'orient': int(match.group(9)),
                        'rect': {
                            'x': int(match.group(10)),
                            'y': int(match.group(11)),
                            'w': int(match.group(12)),
                            'h': int(match.group(13))
                        },
                        # ZOrd > 0 表示窗口在可见层级中
                        'is_visible': zord > 0
                    }
                    windows.append(window_info)
                except (ValueError, IndexError) as e:
                    logger.debug(f"解析窗口信息失败: {line}, 错误: {e}")
                    continue

        logger.info(f"找到 {len(windows)} 个窗口")
        return {
            'success': True,
            'windows': windows,
            'count': len(windows)
        }

    def get_ui_tree_raw(self, device_id: str, window_id: int = None) -> Dict[str, Any]:
        """
        获取UI组件树原始输出（使用 uitest dumpLayout 命令）

        Args:
            device_id: 设备ID
            window_id: 窗口ID（可选，目前 uitest dumpLayout 获取全屏UI树）

        Returns:
            包含UI组件树JSON的字典
        """
        timeout = Config.UI_TREE_TIMEOUT
        
        logger.info(f"获取UI组件树 (device: {device_id}, timeout: {timeout}s)")
        
        # 使用 uitest dumpLayout 命令获取UI树
        # 该命令会将UI树保存到设备上的JSON文件
        dump_result = self.execute_shell(device_id, "uitest dumpLayout", timeout=timeout)
        
        if not dump_result['success']:
            logger.error(f"uitest dumpLayout 失败: {dump_result['stderr']}")
            return {
                'success': False,
                'error': dump_result['stderr'],
                'ui_tree': ''
            }
        
        # 解析输出获取文件路径
        # 输出格式: "DumpLayout saved to:/data/local/tmp/layout_xxx.json"
        output = dump_result['stdout'].strip()
        if 'saved to:' not in output:
            logger.error(f"无法解析 dumpLayout 输出: {output}")
            return {
                'success': False,
                'error': f'无法解析 dumpLayout 输出: {output}',
                'ui_tree': ''
            }
        
        json_path = output.split('saved to:')[-1].strip()
        logger.info(f"UI树保存路径: {json_path}")
        
        # 读取JSON文件内容
        cat_result = self.execute_shell(device_id, f"cat {json_path}", timeout=timeout)
        
        if not cat_result['success']:
            logger.error(f"读取UI树文件失败: {cat_result['stderr']}")
            return {
                'success': False,
                'error': cat_result['stderr'],
                'ui_tree': ''
            }
        
        logger.info(f"成功获取UI组件树，长度: {len(cat_result['stdout'])} 字符")
        return {
            'success': True,
            'window_id': window_id,
            'ui_tree': cat_result['stdout'],
            'format': 'uitest_json'
        }

    def find_window_by_bundle(self, device_id: str, bundle_name: str) -> Optional[int]:
        """
        根据应用包名查找窗口ID

        Args:
            device_id: 设备ID
            bundle_name: 应用包名

        Returns:
            窗口ID，如果未找到则返回None
        """
        logger.info(f"查找应用 {bundle_name} 的窗口")
        window_list = self.get_window_list(device_id)

        if not window_list['success']:
            logger.error("获取窗口列表失败")
            return None

        # 从包名提取应用名称 (如 com.huawei.hmos.settings -> settings)
        app_name = bundle_name.split('.')[-1].lower()
        
        # 查找匹配的可见窗口（优先返回可见窗口）
        for window in window_list['windows']:
            window_name = window['window_name'].lower()
            # 窗口名称通常是 appname + 数字，如 settings0, browser0
            # 检查窗口名是否以应用名开头
            if window_name.startswith(app_name) and window['is_visible']:
                logger.info(f"找到匹配可见窗口: {window['window_name']}, ID: {window['window_id']}")
                return window['window_id']

        # 如果没有找到可见匹配，查找任何匹配的窗口
        for window in window_list['windows']:
            window_name = window['window_name'].lower()
            if window_name.startswith(app_name):
                logger.info(f"找到匹配窗口(不可见): {window['window_name']}, ID: {window['window_id']}")
                return window['window_id']

        logger.warning(f"未找到应用 {bundle_name} 的窗口 (app_name={app_name})")
        return None
