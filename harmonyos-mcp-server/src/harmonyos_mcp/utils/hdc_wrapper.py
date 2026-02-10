"""
hdc命令行工具封装
"""
import asyncio
import subprocess
import time
import re
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from loguru import logger

from harmonyos_mcp.config import Config
from harmonyos_mcp.utils.retry import retry, is_transient_hdc_failure


class HdcWrapper:
    """HarmonyOS Device Connector (hdc) 工具封装类"""
    
    def __init__(self, hdc_path: Optional[str] = None):
        """
        初始化hdc包装器
        
        Args:
            hdc_path: hdc工具路径,如果为None则使用配置中的路径
        """
        Config.ensure_init()
        self.hdc_path = hdc_path or Config.HDC_PATH
        if not self.hdc_path:
            raise ValueError("hdc工具路径未配置")
        
        logger.info(f"初始化HdcWrapper, hdc路径: {self.hdc_path}")
    
    @retry(should_retry=is_transient_hdc_failure)
    def _execute_command(self, args: List[str], timeout: int = None) -> Dict[str, Any]:
        """
        执行hdc命令
        
        Args:
            args: 命令参数列表
            timeout: 超时时间(秒)
        
        Returns:
            包含returncode, stdout, stderr的字典
        """
        cmd = [self.hdc_path] + args
        timeout = timeout or Config.COMMAND_TIMEOUT
        
        logger.debug(f"执行命令: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding='utf-8',
                errors='ignore'
            )
            
            return {
                'returncode': result.returncode,
                'stdout': result.stdout.strip(),
                'stderr': result.stderr.strip(),
                'success': result.returncode == 0
            }
        except subprocess.TimeoutExpired:
            logger.error(f"命令执行超时: {' '.join(cmd)}")
            return {
                'returncode': -1,
                'stdout': '',
                'stderr': f'命令执行超时({timeout}秒)',
                'success': False
            }
        except Exception as e:
            logger.error(f"命令执行失败: {e}")
            return {
                'returncode': -1,
                'stdout': '',
                'stderr': str(e),
                'success': False
            }
    
    async def _execute_command_async(self, args: List[str], timeout: int = None) -> Dict[str, Any]:
        """
        异步执行hdc命令（使用 asyncio.create_subprocess_exec）
        
        与 _execute_command 语义一致，但不阻塞事件循环。
        适用于在 async 上下文中调用，例如 FastMCP 异步工具函数。
        
        Args:
            args: 命令参数列表
            timeout: 超时时间(秒)
        
        Returns:
            包含returncode, stdout, stderr的字典
        """
        cmd = [self.hdc_path] + args
        timeout = timeout or Config.COMMAND_TIMEOUT
        
        logger.debug(f"异步执行命令: {' '.join(cmd)}")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            return {
                'returncode': process.returncode,
                'stdout': stdout_bytes.decode('utf-8', errors='ignore').strip(),
                'stderr': stderr_bytes.decode('utf-8', errors='ignore').strip(),
                'success': process.returncode == 0
            }
        except asyncio.TimeoutError:
            logger.error(f"异步命令执行超时: {' '.join(cmd)}")
            try:
                process.kill()
                await process.wait()
            except Exception:
                pass
            return {
                'returncode': -1,
                'stdout': '',
                'stderr': f'命令执行超时({timeout}秒)',
                'success': False
            }
        except Exception as e:
            logger.error(f"异步命令执行失败: {e}")
            return {
                'returncode': -1,
                'stdout': '',
                'stderr': str(e),
                'success': False
            }
    
    def list_devices(self) -> List[str]:
        """
        列出所有连接的设备
        
        Returns:
            设备ID列表
        """
        logger.info("获取设备列表")
        result = self._execute_command(['list', 'targets'])
        
        if not result['success']:
            logger.error(f"获取设备列表失败: {result['stderr']}")
            return []
        
        devices = [line.strip() for line in result['stdout'].split('\n') if line.strip()]
        logger.info(f"找到 {len(devices)} 个设备: {devices}")
        return devices
    
    def install_app(self, device_id: str, hap_path: str) -> bool:
        """
        安装应用到设备
        
        Args:
            device_id: 设备ID
            hap_path: HAP包路径
        
        Returns:
            是否安装成功
        """
        logger.info(f"安装应用到设备 {device_id}: {hap_path}")
        result = self._execute_command(
            ['-t', device_id, 'install', hap_path],
            timeout=Config.INSTALL_TIMEOUT
        )
        
        if result['success']:
            logger.info(f"应用安装成功")
            return True
        else:
            logger.error(f"应用安装失败: {result['stderr']}")
            return False

    def uninstall_app(self, device_id: str, bundle_name: str) -> bool:
        """
        卸载应用

        Args:
            device_id: 设备ID
            bundle_name: 应用包名

        Returns:
            是否卸载成功
        """
        logger.info(f"从设备 {device_id} 卸载应用: {bundle_name}")
        result = self._execute_command(['-t', device_id, 'uninstall', bundle_name])

        if result['success']:
            logger.info(f"应用卸载成功")
            return True
        else:
            logger.error(f"应用卸载失败: {result['stderr']}")
            return False

    def execute_shell(self, device_id: str, command: str, timeout: int = None) -> Dict[str, Any]:
        """
        在设备上执行Shell命令

        Args:
            device_id: 设备ID
            command: Shell命令
            timeout: 超时时间(秒)，默认使用 COMMAND_TIMEOUT

        Returns:
            命令执行结果
        """
        logger.debug(f"在设备 {device_id} 上执行Shell命令: {command}" + (f", 超时: {timeout}s" if timeout else ""))
        result = self._execute_command(['-t', device_id, 'shell', command], timeout=timeout)
        return result

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

    def list_hilog_files(self, device_id: str, hilog_dir: str = "/data/log/hilog") -> Dict[str, Any]:
        """
        列出设备上 hilog 目录下的日志文件
        
        Args:
            device_id: 设备ID
            hilog_dir: hilog 目录路径，默认 /data/log/hilog
        
        Returns:
            包含文件列表的字典，每个文件包含 name, size, timestamp 信息
        """
        logger.info(f"列出设备 {device_id} 的 hilog 文件: {hilog_dir}")
        
        # 使用 ls -la 获取文件详情
        result = self.execute_shell(device_id, f'ls -la {hilog_dir}')
        
        if not result['success']:
            return {
                'success': False,
                'error': result.get('stderr', '无法访问 hilog 目录'),
                'files': [],
                'raw_output': result.get('stdout', '')
            }
        
        files = []
        raw_lines = []
        
        # 解析 ls 输出，提取 hilog 文件信息
        for line in result['stdout'].split('\n'):
            line = line.strip()
            if not line or line.startswith('total'):
                continue
            
            raw_lines.append(line)
            
            # 跳过目录
            if line.startswith('d'):
                continue
            
            parts = line.split()
            if len(parts) < 6:
                continue
            
            # 文件名是最后一个字段
            filename = parts[-1]
            
            # 只处理 hilog 文件
            if not (filename.startswith('hilog') or 'hilog' in filename):
                continue
            
            try:
                # 尝试找到文件大小（通常是第一个纯数字字段，且值较大）
                size = 0
                for part in parts[1:-1]:
                    if part.isdigit() and int(part) > 100:
                        size = int(part)
                        break
                
                # 尝试从文件名提取时间戳
                # 支持格式: hilog.658.20260203-201355 或 hilog.658.20260203-201355.gz
                timestamp = None
                from datetime import datetime
                
                # 移除 .gz 后缀
                name_without_gz = filename.rstrip('.gz')
                
                # 尝试多种时间戳提取方式
                if '-' in name_without_gz:
                    # 格式: hilog.658.20260203-201355
                    time_part = name_without_gz.split('.')[-1]
                    if len(time_part) >= 15 and time_part[0].isdigit():
                        try:
                            timestamp = datetime.strptime(time_part, '%Y%m%d-%H%M%S')
                        except ValueError:
                            # 尝试只解析日期部分
                            try:
                                date_part = time_part.split('-')[0]
                                if len(date_part) == 8:
                                    timestamp = datetime.strptime(date_part, '%Y%m%d')
                            except ValueError:
                                pass
                
                files.append({
                    'name': filename,
                    'path': f"{hilog_dir}/{filename}",
                    'size': size,
                    'timestamp': timestamp.isoformat() if timestamp else None,
                    'timestamp_dt': timestamp
                })
                logger.debug(f"找到 hilog 文件: {filename}, 时间戳: {timestamp}")
                
            except (ValueError, IndexError) as e:
                logger.warning(f"解析文件信息失败: {line}, 错误: {e}")
                continue
        
        # 按时间戳排序（最新的在前）
        files.sort(key=lambda x: x.get('timestamp') or '', reverse=True)
        
        return {
            'success': True,
            'files': files,
            'count': len(files),
            'directory': hilog_dir,
            'raw_line_count': len(raw_lines)
        }

    def pull_hilog_files(
        self, 
        device_id: str, 
        files: List[Dict], 
        local_dir: str,
        start_time: 'datetime' = None,
        end_time: 'datetime' = None
    ) -> Dict[str, Any]:
        """
        从设备拉取 hilog 文件到本地
        
        Args:
            device_id: 设备ID
            files: 文件列表（来自 list_hilog_files）
            local_dir: 本地保存目录
            start_time: 开始时间过滤
            end_time: 结束时间过滤
        
        Returns:
            拉取结果，包含成功拉取的文件列表
        """
        import os
        from datetime import datetime
        
        os.makedirs(local_dir, exist_ok=True)
        
        pulled_files = []
        failed_files = []
        
        for file_info in files:
            # 时间范围过滤
            file_ts = file_info.get('timestamp_dt')
            if file_ts:
                if start_time and file_ts < start_time:
                    continue
                if end_time and file_ts > end_time:
                    continue
            
            remote_path = file_info['path']
            local_path = os.path.join(local_dir, file_info['name'])
            
            logger.info(f"拉取 hilog 文件: {remote_path} -> {local_path}")
            
            if self.pull_file(device_id, remote_path, local_path):
                pulled_files.append({
                    'name': file_info['name'],
                    'local_path': local_path,
                    'size': file_info['size'],
                    'timestamp': file_info.get('timestamp')
                })
            else:
                failed_files.append(file_info['name'])
        
        return {
            'success': len(pulled_files) > 0,
            'pulled_files': pulled_files,
            'failed_files': failed_files,
            'local_dir': local_dir
        }

    def get_realtime_logs(self, device_id: str, lines: int = 100, tag: Optional[str] = None,
                 bundle_name: Optional[str] = None, pid: Optional[int] = None) -> str:
        """
        获取设备实时日志（hilog 缓存）

        Args:
            device_id: 设备ID
            lines: 日志行数
            tag: 日志标签过滤
            bundle_name: 应用包名过滤（通过grep实现）
            pid: 进程ID过滤

        Returns:
            日志内容
        """
        logger.info(f"获取设备 {device_id} 的实时日志")

        # 构建hilog命令
        cmd = ['-t', device_id, 'shell']

        # 构建hilog命令字符串
        # 使用 -x 参数只获取当前缓存的日志，不持续输出
        hilog_cmd = 'hilog -x'

        # 添加标签过滤
        if tag:
            hilog_cmd += f' -T {tag}'

        # 添加进程ID过滤
        if pid:
            hilog_cmd += f' -P {pid}'

        # 如果需要按包名过滤，使用grep
        if bundle_name:
            hilog_cmd += f' | grep "{bundle_name}"'

        cmd.append(hilog_cmd)

        # 执行命令
        result = self._execute_command(cmd, timeout=10)

        if result['success']:
            log_lines = result['stdout'].split('\n')
            # 过滤空行
            log_lines = [line for line in log_lines if line.strip()]
            # 返回最后N行
            return '\n'.join(log_lines[-lines:])
        else:
            logger.error(f"获取日志失败: {result['stderr']}")
            return ""

    def start_app(self, device_id: str, bundle_name: str, ability_name: str = "EntryAbility", module_name: str = "entry", verify: bool = True, timeout: float = 3.0) -> Dict[str, Any]:
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
        import time
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

    def push_file(self, device_id: str, local_path: str, remote_path: str) -> bool:
        """
        推送文件到设备

        Args:
            device_id: 设备ID
            local_path: 本地文件路径
            remote_path: 设备文件路径

        Returns:
            是否推送成功
        """
        logger.info(f"推送文件: {local_path} -> {remote_path}")
        result = self._execute_command([
            '-t', device_id,
            'file', 'send',
            local_path,
            remote_path
        ])

        if result['success']:
            logger.info(f"文件推送成功")
            return True
        else:
            logger.error(f"文件推送失败: {result['stderr']}")
            return False

    def pull_file(self, device_id: str, remote_path: str, local_path: str) -> bool:
        """
        从设备拉取文件

        Args:
            device_id: 设备ID
            remote_path: 设备文件路径
            local_path: 本地文件路径

        Returns:
            是否拉取成功
        """
        logger.info(f"拉取文件: {remote_path} -> {local_path}")
        result = self._execute_command([
            '-t', device_id,
            'file', 'recv',
            remote_path,
            local_path
        ])

        if result['success']:
            logger.info(f"文件拉取成功")
            return True
        else:
            logger.error(f"文件拉取失败: {result['stderr']}")
            return False

    # ========================================================================
    # hidumper工具相关方法 - UI组件树获取
    # ========================================================================

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
        import re
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
        from harmonyos_mcp.config import Config
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

    # ========================================================================
    # hilog文件相关方法 - 获取系统日志文件
    # ========================================================================

    def hilog_receive(self, device_id: str, local_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        从设备的 /data/log/hilog 目录中获取所有 hilog 日志文件和 dict 解密文件

        Args:
            device_id: 设备ID
            local_dir: 本地保存目录，如果为None则使用当前工作目录

        Returns:
            包含成功状态、获取的文件列表和详细信息的字典
        """
        logger.info(f"开始获取设备 {device_id} 的 hilog 文件")
        
        # 如果没有指定目录，使用当前工作目录下的 hilog_files 子目录
        if not local_dir:
            local_dir = os.path.join(os.getcwd(), 'hilog_files')
        
        local_dir = os.path.abspath(local_dir)
        
        # 确保本地目录存在
        os.makedirs(local_dir, exist_ok=True)
        logger.info(f"本地目录: {local_dir}")
        
        # 步骤1: 列出 /data/log/hilog 目录下的所有文件
        logger.info("列出设备 /data/log/hilog 目录文件...")
        list_cmd = "ls -la /data/log/hilog"
        result = self.execute_shell(device_id, list_cmd)
        
        if not result['success']:
            error_msg = f"无法访问 /data/log/hilog 目录: {result.get('stderr', '未知错误')}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'files_received': [],
                'count': 0
            }
        
        # 步骤2: 解析文件列表，找出 hilog 和 dict 文件
        hilog_files = []
        dict_files = []
        
        for line in result['stdout'].split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # 解析 ls -la 的输出，获取文件名（最后一列）
            parts = line.split()
            if len(parts) >= 8:  # ls -la 至少有 8 列
                filename = parts[-1]
                logger.debug(f"解析行: {len(parts)}列 => 文件名: {filename}")
                
                # 匹配 hilog.*.gz 文件
                if filename.startswith('hilog.') and filename.endswith('.gz'):
                    hilog_files.append(filename)
                    logger.debug(f"发现 hilog 文件: {filename}")
                
                # 匹配 hilog_dict.*.zip 文件
                elif filename.startswith('hilog_dict.') and filename.endswith('.zip'):
                    dict_files.append(filename)
                    logger.debug(f"发现 dict 文件: {filename}")
        
        logger.info(f"找到 {len(hilog_files)} 个 hilog 文件, {len(dict_files)} 个 dict 文件")
        
        if not hilog_files and not dict_files:
            warning_msg = "/data/log/hilog 目录中没有找到任何 hilog 或 dict 文件"
            logger.warning(warning_msg)
            return {
                'success': True,
                'warning': warning_msg,
                'files_received': [],
                'count': 0
            }
        
        # 步骤3: 拉取所有文件到本地
        files_received = []
        failed_files = []
        
        for filename in hilog_files + dict_files:
            remote_path = f"/data/log/hilog/{filename}"
            local_path = os.path.join(local_dir, filename)
            
            logger.info(f"拉取文件: {remote_path} -> {local_path}")
            
            if self.pull_file(device_id, remote_path, local_path):
                files_received.append({
                    'filename': filename,
                    'local_path': local_path,
                    'type': 'hilog' if filename.endswith('.gz') else 'dict',
                    'size': os.path.getsize(local_path) if os.path.exists(local_path) else 0
                })
                logger.info(f"✓ 成功拉取: {filename}")
            else:
                failed_files.append(filename)
                logger.error(f"✗ 拉取失败: {filename}")
        
        logger.info(f"共获取 {len(files_received)} 个文件，失败 {len(failed_files)} 个")
        
        return {
            'success': True,
            'files_received': files_received,
            'count': len(files_received),
            'failed_count': len(failed_files),
            'failed_files': failed_files,
            'local_dir': local_dir,
            'hilog_count': sum(1 for f in files_received if f['type'] == 'hilog'),
            'dict_count': sum(1 for f in files_received if f['type'] == 'dict')
        }

    # ========================================================================
    # Bundle Manager (bm) 工具相关方法 - 包管理与Ability查询
    # ========================================================================

    def list_packages(self, device_id: str, keyword: Optional[str] = None) -> Dict[str, Any]:
        """
        列出设备上已安装的应用包

        Args:
            device_id: 设备ID
            keyword: 可选的关键字过滤

        Returns:
            包含包列表的字典
        """
        logger.info(f"获取设备 {device_id} 的已安装包列表")
        
        # 使用 bm dump -a 获取所有包
        command = "bm dump -a"
        result = self.execute_shell(device_id, command)

        if not result['success']:
            logger.error(f"获取包列表失败: {result['stderr']}")
            return {
                'success': False,
                'error': result['stderr'],
                'packages': []
            }

        # 解析输出，提取包名
        packages = []
        lines = result['stdout'].split('\n')
        
        for line in lines:
            line = line.strip()
            # bm dump -a 输出格式通常是每行一个包名
            if line and not line.startswith('[') and not line.startswith('ID'):
                # 过滤掉非包名的行
                if '.' in line and not line.startswith('-'):
                    package_name = line.strip()
                    # 如果有关键字过滤
                    if keyword:
                        if keyword.lower() in package_name.lower():
                            packages.append(package_name)
                    else:
                        packages.append(package_name)

        logger.info(f"找到 {len(packages)} 个包")
        return {
            'success': True,
            'packages': packages,
            'count': len(packages),
            'keyword': keyword
        }

    def get_package_info(self, device_id: str, bundle_name: str) -> Dict[str, Any]:
        """
        获取指定包的详细信息，包括所有Abilities

        Args:
            device_id: 设备ID
            bundle_name: 应用包名

        Returns:
            包含包详细信息和Abilities列表的字典
        """
        logger.info(f"获取包 {bundle_name} 的详细信息")
        
        # 使用 bm dump -n 获取包详情
        command = f"bm dump -n {bundle_name}"
        result = self.execute_shell(device_id, command)

        if not result['success']:
            logger.error(f"获取包信息失败: {result['stderr']}")
            return {
                'success': False,
                'error': result['stderr'],
                'bundle_name': bundle_name
            }

        output = result['stdout']
        
        # 检查是否找到包 - 更精确的判断
        # bm dump 在包不存在时会返回类似 "error: failed to get bundle info" 的错误
        first_line = output.split('\n')[0].strip().lower() if output else ''
        if ('not found' in first_line or 
            ('error' in first_line and 'failed' in first_line) or
            output.strip().startswith('error:')):
            return {
                'success': False,
                'error': f'包 {bundle_name} 未找到',
                'bundle_name': bundle_name
            }

        # 解析Abilities和模块信息
        parse_result = self._parse_abilities_from_dump(output)
        abilities = parse_result['abilities']
        modules = parse_result['modules']
        module_main_abilities = parse_result['module_main_abilities']
        entry_module_name = parse_result.get('entry_module_name', '')
        
        # 查找主Ability
        main_ability_result = self._find_main_ability(abilities, modules, module_main_abilities)
        
        # 检查是否有可启动的入口
        has_launcher = any(a.get('hasHomeAction', False) for a in abilities)

        return {
            'success': True,
            'bundle_name': bundle_name,
            'has_launcher_ability': has_launcher,
            'abilities': abilities,
            'modules': modules,
            'entry_module_name': entry_module_name,
            'module_main_abilities': module_main_abilities,
            'main_ability': main_ability_result.get('ability') if main_ability_result else None,
            'raw_output': output
        }

    def _parse_abilities_from_dump(self, dump_output: str) -> Dict[str, Any]:
        """
        从bm dump输出中解析Abilities信息（使用JSON解析）

        Args:
            dump_output: bm dump命令的原始输出

        Returns:
            包含 abilities, modules, module_main_abilities, entry_module_name 的字典
        """
        import json
        
        abilities = []
        modules = []
        module_main_abilities = {}  # {module_name: main_ability_name}
        entry_module_name = ''  # 包级别声明的入口模块
        
        try:
            # bm dump 输出格式: "包名:\n{json}"
            lines = dump_output.split('\n', 1)
            if len(lines) > 1:
                json_str = lines[1] if ':' in lines[0] else dump_output
            else:
                json_str = dump_output
            
            data = json.loads(json_str)
            
            # 获取包级别的 entryModuleName
            entry_module_name = data.get('entryModuleName', '')
            
            # 遍历 hapModuleInfos
            for hap in data.get('hapModuleInfos', []):
                module_name = hap.get('moduleName', 'entry')
                
                # 记录模块信息
                if module_name not in [m['name'] for m in modules]:
                    modules.append({'name': module_name})
                
                # 获取模块级 mainAbility/mainElementName 声明
                main_ability = hap.get('mainAbility') or hap.get('mainElementName')
                if main_ability:
                    module_main_abilities[module_name] = main_ability
                
                for ability_info in hap.get('abilityInfos', []):
                    ability = {
                        'name': ability_info.get('name', ''),
                        'type': 'page' if ability_info.get('type', 0) == 1 else 'service',
                        'visible': ability_info.get('visible', False),
                        'module': ability_info.get('moduleName', module_name),
                        'isLauncherAbility': ability_info.get('isLauncherAbility', False),
                        'skills': ability_info.get('skills', []),
                        'hasHomeAction': False
                    }
                    
                    # 检查是否有 Launcher 相关的 action/entity (真正的启动入口)
                    for skill in ability.get('skills', []):
                        actions = skill.get('actions', [])
                        entities = skill.get('entities', [])
                        # 检查 launcher actions
                        launcher_actions = ['action.system.home', 'ohos.want.action.home']
                        if any(a in actions for a in launcher_actions):
                            ability['hasHomeAction'] = True
                            break
                        # 检查 launcher entities
                        if 'entity.system.home' in entities:
                            ability['hasHomeAction'] = True
                            break
                    
                    if ability['name']:
                        abilities.append(ability)
            
            # 如果没有模块信息，添加默认
            if not modules:
                modules.append({'name': 'entry'})
            
            logger.info(f"解析到 {len(abilities)} 个Abilities, {len(modules)} 个模块, entryModule={entry_module_name}")
            return {
                'abilities': abilities,
                'modules': modules,
                'module_main_abilities': module_main_abilities,
                'entry_module_name': entry_module_name
            }
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败，尝试文本解析: {e}")
            # 回退到文本解析方式
            abilities = self._parse_abilities_from_dump_text(dump_output)
            return {
                'abilities': abilities,
                'modules': [{'name': 'entry'}],
                'module_main_abilities': {},
                'entry_module_name': ''
            }

    def _parse_abilities_from_dump_text(self, dump_output: str) -> List[Dict[str, Any]]:
        """
        从bm dump输出中解析Abilities信息（文本解析方式，作为备用）

        Args:
            dump_output: bm dump命令的原始输出

        Returns:
            Abilities列表
        """
        abilities = []
        lines = dump_output.split('\n')
        
        current_ability = None
        in_ability_section = False
        
        for line in lines:
            stripped = line.strip()
            
            # 检测Ability开始
            if 'abilities:' in stripped.lower() or 'abilityInfos' in stripped:
                in_ability_section = True
                continue
            
            # 解析ability名称 - 多种格式支持
            if in_ability_section:
                # 格式1: "name": "EntryAbility"
                if '"name"' in stripped or "'name'" in stripped:
                    match = re.search(r'["\']name["\']\s*:\s*["\']([^"\']+)["\']', stripped)
                    if match:
                        if current_ability:
                            abilities.append(current_ability)
                        current_ability = {
                            'name': match.group(1),
                            'type': 'page',
                            'visible': True,
                            'module': '',
                            'hasHomeAction': False
                        }
                
                # 解析type
                if current_ability and ('type' in stripped.lower()):
                    match = re.search(r'type["\']?\s*[:=]\s*["\']?(\w+)', stripped, re.IGNORECASE)
                    if match:
                        current_ability['type'] = match.group(1)
                
                # 解析visible
                if current_ability and 'visible' in stripped.lower():
                    current_ability['visible'] = 'true' in stripped.lower()
                
                # 解析moduleName
                if current_ability and ('moduleName' in stripped or 'module' in stripped.lower()):
                    match = re.search(r'module[Nn]?ame?["\']?\s*[:=]\s*["\']?(\w+)', stripped)
                    if match:
                        current_ability['module'] = match.group(1)
                
                # 检测 action.system.home
                if current_ability and 'action.system.home' in stripped:
                    current_ability['hasHomeAction'] = True
                
                # 检测Ability结束
                if stripped.startswith('}') or (stripped == '' and current_ability):
                    if current_ability and current_ability.get('name'):
                        abilities.append(current_ability)
                        current_ability = None

        # 添加最后一个ability
        if current_ability and current_ability.get('name'):
            abilities.append(current_ability)

        # 去重
        seen = set()
        unique_abilities = []
        for ability in abilities:
            key = (ability['name'], ability.get('module', ''))
            if key not in seen:
                seen.add(key)
                unique_abilities.append(ability)

        logger.info(f"解析到 {len(unique_abilities)} 个Abilities (文本方式)")
        return unique_abilities

    def _parse_modules_from_dump(self, dump_output: str) -> List[Dict[str, str]]:
        """
        从bm dump输出中解析模块信息

        Args:
            dump_output: bm dump命令的原始输出

        Returns:
            模块列表
        """
        modules = []
        lines = dump_output.split('\n')
        
        for line in lines:
            stripped = line.strip()
            
            # 查找moduleName或module字段
            if 'moduleName' in stripped or ('"module"' in stripped):
                match = re.search(r'module[Nn]?ame?["\']?\s*[:=]\s*["\']?(\w+)', stripped)
                if match:
                    module_name = match.group(1)
                    if module_name and module_name not in [m['name'] for m in modules]:
                        modules.append({'name': module_name})
        
        # 如果没找到，默认添加entry模块
        if not modules:
            modules.append({'name': 'entry'})
        
        return modules

    def _find_main_ability(self, abilities: List[Dict[str, Any]], 
                           modules: List[Dict[str, str]],
                           module_main_abilities: Dict[str, str] = None) -> Optional[Dict[str, Any]]:
        """
        查找主入口Ability

        Args:
            abilities: Abilities列表
            modules: 模块列表
            module_main_abilities: 模块级mainAbility声明 {module_name: ability_name}

        Returns:
            包含 ability 和 detection_method 的字典，如果未找到则返回None
        """
        if not abilities:
            return None

        module_main_abilities = module_main_abilities or {}
        default_module = modules[0]['name'] if modules else 'entry'

        # 1. 优先查找有 action.system.home/ohos.want.action.home 的 ability (真正的 launcher)
        for ability in abilities:
            if ability.get('hasHomeAction', False):
                if not ability.get('module'):
                    ability['module'] = default_module
                logger.info(f"找到主入口Ability (launcher标签): {ability['name']}")
                return {
                    'ability': ability,
                    'is_launcher': True,
                    'detection_method': 'action.system.home'
                }

        # 2. 查找模块级 mainAbility/mainElementName 声明的 ability
        for module_name, main_ability_name in module_main_abilities.items():
            for ability in abilities:
                if ability['name'] == main_ability_name and ability.get('module') == module_name:
                    logger.info(f"找到主入口Ability (模块mainAbility声明): {ability['name']}")
                    return {
                        'ability': ability,
                        'is_launcher': False,
                        'detection_method': 'mainAbility'
                    }

        # 3. 查找 isLauncherAbility=true 的
        for ability in abilities:
            if ability.get('isLauncherAbility', False):
                if not ability.get('module'):
                    ability['module'] = default_module
                logger.info(f"找到主入口Ability (isLauncherAbility): {ability['name']}")
                return {
                    'ability': ability,
                    'is_launcher': True,
                    'detection_method': 'isLauncherAbility'
                }

        # 4. 按名称优先级查找 (支持带包名前缀的名称，如 com.xxx.MainAbility)
        priority_names = ['EntryAbility', 'MainAbility', 'Main', 'Entry']
        
        for priority_name in priority_names:
            for ability in abilities:
                name = ability['name']
                # 精确匹配或以优先名称结尾（支持 com.xxx.MainAbility 形式）
                if name.lower() == priority_name.lower() or name.lower().endswith('.' + priority_name.lower()):
                    if not ability.get('module'):
                        ability['module'] = default_module
                    logger.info(f"找到主入口Ability (名称匹配): {ability['name']}")
                    return {
                        'ability': ability,
                        'is_launcher': False,
                        'detection_method': f'name_match:{priority_name}'
                    }

        # 5. 返回第一个可见的 page 类型 ability
        for ability in abilities:
            if ability.get('visible', True) and ability.get('type', '').lower() == 'page':
                if not ability.get('module'):
                    ability['module'] = default_module
                logger.info(f"找到主入口Ability (可见page): {ability['name']}")
                return {
                    'ability': ability,
                    'is_launcher': False,
                    'detection_method': 'visible_page'
                }

        # 6. 最后返回第一个 ability
        first_ability = abilities[0]
        if not first_ability.get('module'):
            first_ability['module'] = default_module
        logger.info(f"使用第一个Ability作为主入口: {first_ability['name']}")
        return {
            'ability': first_ability,
            'is_launcher': False,
            'detection_method': 'first_ability'
        }

    def get_main_ability(self, device_id: str, bundle_name: str) -> Dict[str, Any]:
        """
        获取指定包的主入口Ability

        Args:
            device_id: 设备ID
            bundle_name: 应用包名

        Returns:
            包含候选Abilities列表的字典
        """
        logger.info(f"获取包 {bundle_name} 的主入口Ability")
        
        # 获取包详情
        package_info = self.get_package_info(device_id, bundle_name)
        
        if not package_info['success']:
            return package_info
        
        abilities = package_info.get('abilities', [])
        modules = package_info.get('modules', [])
        entry_module_name = package_info.get('entry_module_name', '')
        module_main_abilities = package_info.get('module_main_abilities', {})
        
        if not abilities:
            return {
                'success': False,
                'error': f'包 {bundle_name} 没有可用的Ability',
                'bundle_name': bundle_name
            }
        
        # 获取入口模块的 mainAbility
        entry_main_ability = module_main_abilities.get(entry_module_name, '') if entry_module_name else ''
        
        # 构建候选列表
        candidates = []
        
        for ability in abilities:
            ability_name = ability.get('name', '')
            ability_module = ability.get('module', '')
            
            # 判断是否为launcher
            is_launcher = ability.get('hasHomeAction', False)
            
            # 判断是否为入口模块
            is_entry_module = ability_module == entry_module_name if entry_module_name else False
            
            # 判断是否为入口模块的 mainAbility (最高优先级)
            is_entry_main_ability = (is_entry_module and ability_name == entry_main_ability)
            
            # 确定来源说明
            source = self._get_ability_source(ability, is_entry_module, is_entry_main_ability)
            
            candidate = {
                'ability_name': ability_name,
                'module_name': ability_module,
                'is_entry_module': is_entry_module,
                'is_entry_main_ability': is_entry_main_ability,
                'is_launcher': is_launcher,
                'source': source,
                'visible': ability.get('visible', False),
                'type': ability.get('type', 'page')
            }
            candidates.append(candidate)
        
        # 对候选进行排序
        # 优先级: entryModule的mainAbility > launcher+entryModule > launcher > entryModule > 其他
        def sort_key(c):
            score = 0
            if c['is_entry_main_ability']:
                score += 200  # 最高优先级：入口模块的mainAbility
            if c['is_launcher']:
                score += 100
            if c['is_entry_module']:
                score += 50
            if c['visible']:
                score += 10
            if c['type'] == 'page':
                score += 5
            return -score  # 负数实现降序
        
        candidates.sort(key=sort_key)
        
        # 推荐索引
        recommended = 0 if candidates else -1
        
        return {
            'success': True,
            'bundle_name': bundle_name,
            'has_launcher_ability': package_info.get('has_launcher_ability', False),
            'entry_module_name': entry_module_name,
            'candidates': candidates,
            'recommended': recommended,
            # 向后兼容：提供推荐的ability信息
            'ability_name': candidates[recommended]['ability_name'] if recommended >= 0 else '',
            'module_name': candidates[recommended]['module_name'] if recommended >= 0 else 'entry',
            'is_launcher': candidates[recommended]['is_launcher'] if recommended >= 0 else False
        }

    def _get_ability_source(self, ability: Dict[str, Any], is_entry_module: bool, is_entry_main_ability: bool = False) -> str:
        """获取ability来源说明"""
        sources = []
        
        if is_entry_main_ability:
            sources.append('entryModule.mainAbility')
        
        if ability.get('hasHomeAction', False):
            sources.append('action.system.home')
        
        if ability.get('isLauncherAbility', False):
            sources.append('isLauncherAbility')
        
        if is_entry_module and not is_entry_main_ability:
            sources.append('entryModule')
        
        if not sources:
            if ability.get('visible', False) and ability.get('type') == 'page':
                sources.append('可见page类型')
            else:
                sources.append('普通ability')
        
        return ', '.join(sources)
