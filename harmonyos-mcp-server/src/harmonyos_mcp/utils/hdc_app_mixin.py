"""
hdc 应用管理 Mixin

提供应用启动、进程管理、端口转发等功能。
"""
import time
from typing import Optional, Dict, Any
from loguru import logger


class HdcAppMixin:
    """应用管理相关方法"""

    def get_app_pid(self, device_id: str, package_name: str) -> Optional[int]:
        """
        获取应用的进程ID
        
        Args:
            device_id: 设备ID
            package_name: 应用包名 (如 com.example.myapplication)
        
        Returns:
            进程ID，如果应用未运行则返回 None
        """
        logger.debug(f"获取应用 {package_name} 的进程ID")
        
        # 使用 pidof 命令获取进程ID
        result = self.execute_shell(device_id, f'pidof {package_name}')
        
        if result['success'] and result['stdout'].strip():
            try:
                # pidof 可能返回多个 PID（多进程），取第一个
                pid_str = result['stdout'].strip().split()[0]
                pid = int(pid_str)
                logger.info(f"应用 {package_name} 的进程ID: {pid}")
                return pid
            except (ValueError, IndexError):
                logger.warning(f"无法解析进程ID: {result['stdout']}")
                return None
        else:
            logger.debug(f"应用 {package_name} 未运行或未找到进程")
            return None

    def start_app(self, device_id: str, bundle_name: str, ability_name: str = "EntryAbility", 
                  module_name: str = "entry", verify: bool = True, timeout: float = 3.0) -> Dict[str, Any]:
        """
        启动应用

        Args:
            device_id: 设备ID
            bundle_name: 应用包名
            ability_name: Ability名称
            module_name: 模块名称
            verify: 是否验证应用实际启动（检查窗口是否出现）
            timeout: 验证超时时间（秒）

        Returns:
            包含启动状态的字典
        """
        logger.info(f"启动应用: {bundle_name}/{ability_name} (module: {module_name})")

        # 使用aa start命令启动应用，添加-m参数指定模块
        command = f"aa start -a {ability_name} -b {bundle_name} -m {module_name}"
        result = self.execute_shell(device_id, command)

        if not result['success']:
            logger.error(f"应用启动命令失败: {result['stderr']}")
            return {
                'success': False,
                'error': result['stderr'],
                'command_success': False,
                'window_found': False
            }

        # 如果不需要验证，直接返回命令执行结果
        if not verify:
            return {
                'success': True,
                'command_success': True,
                'window_found': None,
                'message': '启动命令已执行（未验证窗口）'
            }

        # 验证应用实际启动：检查窗口是否出现
        app_name = bundle_name.split('.')[-1].lower()
        start_time = time.time()
        window_found = False
        window_info = None

        while time.time() - start_time < timeout:
            window_list = self.get_window_list(device_id)
            if window_list['success']:
                for window in window_list['windows']:
                    window_name = window['window_name'].lower()
                    if window_name.startswith(app_name) and window['is_visible']:
                        window_found = True
                        window_info = {
                            'window_name': window['window_name'],
                            'window_id': window['window_id'],
                            'zord': window.get('zord'),
                            'rect': window.get('rect')
                        }
                        break
            if window_found:
                break
            time.sleep(0.3)

        if window_found:
            logger.info(f"应用启动成功，窗口已出现: {window_info['window_name']}")
            return {
                'success': True,
                'command_success': True,
                'window_found': True,
                'window': window_info
            }
        else:
            logger.warning(f"应用启动命令成功，但未检测到窗口 (app_name={app_name})")
            return {
                'success': False,
                'error': f'应用窗口未出现（可能ability_name或module_name错误）',
                'command_success': True,
                'window_found': False
            }

    def forward_port(self, device_id: str, local_port: int, remote_port: int) -> bool:
        """
        端口转发

        Args:
            device_id: 设备ID
            local_port: 本地端口
            remote_port: 远程端口

        Returns:
            是否转发成功
        """
        logger.info(f"设置端口转发: localhost:{local_port} -> device:{remote_port}")
        result = self._execute_command([
            '-t', device_id,
            'fport',
            f'tcp:{local_port}',
            f'tcp:{remote_port}'
        ])

        if result['success']:
            logger.info(f"端口转发设置成功")
            return True
        else:
            logger.error(f"端口转发设置失败: {result['stderr']}")
            return False
