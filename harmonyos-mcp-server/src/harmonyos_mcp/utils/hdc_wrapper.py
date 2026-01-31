"""
hdc命令行工具封装
"""
import subprocess
import time
import re
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from loguru import logger

from ..config import Config


class HdcWrapper:
    """HarmonyOS Device Connector (hdc) 工具封装类"""
    
    def __init__(self, hdc_path: Optional[str] = None):
        """
        初始化hdc包装器
        
        Args:
            hdc_path: hdc工具路径,如果为None则使用配置中的路径
        """
        self.hdc_path = hdc_path or Config.HDC_PATH
        if not self.hdc_path:
            raise ValueError("hdc工具路径未配置")
        
        logger.info(f"初始化HdcWrapper, hdc路径: {self.hdc_path}")
    
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

    def execute_shell(self, device_id: str, command: str) -> Dict[str, Any]:
        """
        在设备上执行Shell命令

        Args:
            device_id: 设备ID
            command: Shell命令

        Returns:
            命令执行结果
        """
        logger.debug(f"在设备 {device_id} 上执行Shell命令: {command}")
        result = self._execute_command(['-t', device_id, 'shell', command])
        return result

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
        logger.info(f"获取UI组件树 (device: {device_id})")
        
        # 使用 uitest dumpLayout 命令获取UI树
        # 该命令会将UI树保存到设备上的JSON文件
        dump_result = self.execute_shell(device_id, "uitest dumpLayout")
        
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
        cat_result = self.execute_shell(device_id, f"cat {json_path}")
        
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
    # 三方库鸿蒙化编译相关方法
    # ========================================================================

    def check_wsl_available(self) -> Dict[str, Any]:
        """
        检查当前系统是否可用 WSL 环境

        Returns:
            检查结果与提示信息
        """
        import platform
        
        system = platform.system()
        
        if system != "Windows":
            return {
                "status": "not_windows",
                "message": f"当前系统 {system}，无需使用 WSL",
                "can_compile": True,
            }

        # Windows 系统检查 WSL
        try:
            result = subprocess.run(
                ["wsl", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return {
                    "status": "available",
                    "message": "检测到 WSL，可在 WSL 中执行鸿蒙化编译",
                    "can_compile": True,
                    "wsl_version": result.stdout.strip(),
                }
        except Exception as e:
            logger.debug(f"WSL 检查失败: {e}")

        return {
            "status": "missing",
            "message": "Windows 系统检测不到 WSL，请先安装 WSL 环境后再进行鸿蒙化交叉编译",
            "can_compile": False,
            "action": "install_wsl",
            "guidance": "请参考 https://learn.microsoft.com/zh-cn/windows/wsl/install",
        }

    def check_harmonyos_compiler_tools(self, tools_dir: str = "./harmonyos_commandline_tools") -> Dict[str, Any]:
        """
        检查 HarmonyOS Command Line Tools 是否已安装

        Args:
            tools_dir: HarmonyOS CommandLine Tools 所在目录

        Returns:
            检查结果
        """
        abs_tools_dir = os.path.abspath(tools_dir)
        
        if not os.path.exists(abs_tools_dir):
            return {
                "status": "missing",
                "message": f"HarmonyOS CommandLine Tools 目录不存在: {abs_tools_dir}",
                "can_compile": False,
                "action": "download_and_extract",
                "guidance": "请从官方网站下载 HarmonyOS Command Line Tool 并解压到指定目录",
                "doc": "https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/ide-commandline-get",
            }

        return {
            "status": "present",
            "message": f"检测到 HarmonyOS CommandLine Tools: {abs_tools_dir}",
            "can_compile": True,
            "tools_dir": abs_tools_dir,
        }

    def clone_library(self, repo_url: str, local_path: str, version: str = None) -> Dict[str, Any]:
        """
        拉取三方库代码仓库并切换到指定版本

        Args:
            repo_url: 仓库 URL (git/https)
            local_path: 本地存放路径
            version: 可选，指定版本（tag/branch/commit），如 "v1.1.1w" 或 "OpenSSL_1_1_1w"

        Returns:
            拉取结果
        """
        logger.info(f"开始拉取三方库: {repo_url} -> {local_path} (版本: {version or 'default'})")
        
        # 确保本地目录存在
        parent_dir = os.path.dirname(os.path.abspath(local_path))
        os.makedirs(parent_dir, exist_ok=True)
        
        # 检查是否已存在
        if os.path.exists(local_path):
            return {
                "success": False,
                "error": f"目录已存在: {local_path}，请先删除或使用其他路径",
            }

        try:
            # 如果指定了版本，使用 --branch 参数直接clone指定分支/tag
            if version:
                clone_cmd = ["git", "clone", "--depth", "1", "--branch", version, repo_url, local_path]
            else:
                clone_cmd = ["git", "clone", repo_url, local_path]
            
            result = subprocess.run(
                clone_cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                logger.info(f"成功拉取三方库: {local_path}")
                return {
                    "success": True,
                    "repo_url": repo_url,
                    "local_path": os.path.abspath(local_path),
                    "version": version or "default",
                }
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                logger.error(f"拉取失败: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "拉取超时 (300秒)",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def analyze_build_system(self, project_dir: str) -> Dict[str, Any]:
        """
        分析项目的构建系统类型

        Args:
            project_dir: 项目目录

        Returns:
            构建系统分析结果
        """
        logger.info(f"分析项目构建系统: {project_dir}")
        
        if not os.path.exists(project_dir):
            return {
                "success": False,
                "error": f"项目目录不存在: {project_dir}",
            }

        build_systems = {}
        
        # 检查各种构建系统文件
        build_system_markers = {
            "GN": ["BUILD.gn", "build.gn"],
            "CMake": ["CMakeLists.txt"],
            "Makefile": ["Makefile", "makefile", "GNUmakefile"],
            "Autotools": ["configure.ac", "Makefile.am", "configure"],
            "Meson": ["meson.build"],
            "Gradle": ["build.gradle", "build.gradle.kts"],
            "Cargo": ["Cargo.toml"],
        }

        for build_system, markers in build_system_markers.items():
            for marker in markers:
                if os.path.exists(os.path.join(project_dir, marker)):
                    build_systems[build_system] = marker
                    break

        if not build_systems:
            return {
                "success": True,
                "detected_systems": [],
                "message": "未检测到已知构建系统，可能需要手动配置",
            }

        return {
            "success": True,
            "detected_systems": list(build_systems.keys()),
            "markers": build_systems,
            "primary_system": list(build_systems.keys())[0],  # 优先级按字典顺序
        }

    def compile_library(
        self,
        project_dir: str,
        build_system: str,
        tools_dir: str = None,
        output_dir: str = None,
        extra_args: List[str] = None
    ) -> Dict[str, Any]:
        """
        使用鸿蒙工具链编译三方库

        Args:
            project_dir: 项目目录
            build_system: 构建系统类型 (cmake/makefile/autotools/gn等)
            tools_dir: HarmonyOS CommandLine Tools 目录路径
            output_dir: 输出目录（可选）
            extra_args: 额外的编译参数（可选）

        Returns:
            编译结果
        """
        logger.info(f"开始编译三方库: {project_dir}, 构建系统: {build_system}")
        
        if not os.path.exists(project_dir):
            return {
                "success": False,
                "error": f"项目目录不存在: {project_dir}",
            }

        # 如果未指定工具目录，尝试使用当前目录下的 harmonyos_commandline_tools
        if not tools_dir:
            tools_dir = os.path.join(os.getcwd(), "harmonyos_commandline_tools")
        
        tools_dir = os.path.abspath(tools_dir)
        
        if not os.path.exists(tools_dir):
            return {
                "success": False,
                "error": f"HarmonyOS CommandLine Tools 目录不存在: {tools_dir}",
                "guidance": "请先下载并配置 HarmonyOS CommandLine Tools",
            }

        # 设置输出目录
        if not output_dir:
            output_dir = os.path.join(project_dir, "build_harmonyos")
        
        os.makedirs(output_dir, exist_ok=True)

        # 根据构建系统选择编译命令
        build_system_lower = build_system.lower()
        
        try:
            if build_system_lower == "cmake":
                # CMake 构建
                result = self._compile_with_cmake(
                    project_dir, tools_dir, output_dir, extra_args or []
                )
            elif build_system_lower in ["makefile", "make"]:
                # Makefile 构建
                result = self._compile_with_make(
                    project_dir, tools_dir, output_dir, extra_args or []
                )
            elif build_system_lower in ["autotools", "configure"]:
                # Autotools 构建
                result = self._compile_with_autotools(
                    project_dir, tools_dir, output_dir, extra_args or []
                )
            elif build_system_lower == "gn":
                # GN 构建
                result = self._compile_with_gn(
                    project_dir, tools_dir, output_dir, extra_args or []
                )
            else:
                return {
                    "success": False,
                    "error": f"不支持的构建系统: {build_system}",
                    "supported_systems": ["cmake", "makefile", "autotools", "gn"],
                }
            
            return result
            
        except Exception as e:
            logger.error(f"编译过程出现异常: {str(e)}")
            return {
                "success": False,
                "error": f"编译异常: {str(e)}",
            }

    def _compile_with_cmake(
        self, 
        project_dir: str, 
        tools_dir: str, 
        output_dir: str, 
        extra_args: List[str]
    ) -> Dict[str, Any]:
        """使用 CMake 编译"""
        logger.info("使用 CMake 编译")
        
        # 查找工具链文件
        toolchain_file = self._find_toolchain_file(tools_dir, "ohos.toolchain.cmake")
        
        if not toolchain_file:
            return {
                "success": False,
                "error": "未找到 HarmonyOS CMake 工具链文件 (ohos.toolchain.cmake)",
                "guidance": "请检查 HarmonyOS CommandLine Tools 是否完整安装",
            }

        # 配置命令
        cmake_cmd = [
            "cmake",
            "-S", project_dir,
            "-B", output_dir,
            f"-DCMAKE_TOOLCHAIN_FILE={toolchain_file}",
            "-DCMAKE_BUILD_TYPE=Release",
            *extra_args
        ]
        
        logger.info(f"配置命令: {' '.join(cmake_cmd)}")
        
        # 执行配置
        config_result = subprocess.run(
            cmake_cmd,
            capture_output=True,
            text=True,
            timeout=600
        )
        
        if config_result.returncode != 0:
            return {
                "success": False,
                "phase": "configure",
                "error": config_result.stderr.strip() or config_result.stdout.strip(),
            }

        # 执行编译
        build_cmd = ["cmake", "--build", output_dir, "--", "-j4"]
        logger.info(f"编译命令: {' '.join(build_cmd)}")
        
        build_result = subprocess.run(
            build_cmd,
            capture_output=True,
            text=True,
            timeout=1800
        )
        
        if build_result.returncode != 0:
            return {
                "success": False,
                "phase": "build",
                "error": build_result.stderr.strip() or build_result.stdout.strip(),
            }

        # 查找生成的 .so 文件
        so_files = self._find_so_files(output_dir)
        
        return {
            "success": True,
            "build_system": "cmake",
            "output_dir": output_dir,
            "so_files": so_files,
            "so_count": len(so_files),
        }

    def _compile_with_make(
        self, 
        project_dir: str, 
        tools_dir: str, 
        output_dir: str, 
        extra_args: List[str]
    ) -> Dict[str, Any]:
        """使用 Make 编译"""
        logger.info("使用 Make 编译")
        
        # 查找工具链环境变量设置脚本
        env_script = self._find_env_script(tools_dir)
        
        if not env_script:
            return {
                "success": False,
                "error": "未找到 HarmonyOS 工具链环境配置脚本",
                "guidance": "需要手动配置交叉编译环境变量",
            }

        # 在 WSL 中执行编译（Windows环境）
        make_cmd = [
            "wsl", "bash", "-c",
            f"cd {project_dir} && source {env_script} && make {' '.join(extra_args)}"
        ]
        
        logger.info(f"编译命令: {' '.join(make_cmd)}")
        
        result = subprocess.run(
            make_cmd,
            capture_output=True,
            text=True,
            timeout=1800
        )
        
        if result.returncode != 0:
            return {
                "success": False,
                "phase": "build",
                "error": result.stderr.strip() or result.stdout.strip(),
            }

        # 查找生成的 .so 文件
        so_files = self._find_so_files(project_dir)
        
        return {
            "success": True,
            "build_system": "make",
            "output_dir": project_dir,
            "so_files": so_files,
            "so_count": len(so_files),
        }

    def _compile_with_autotools(
        self, 
        project_dir: str, 
        tools_dir: str, 
        output_dir: str, 
        extra_args: List[str]
    ) -> Dict[str, Any]:
        """使用 Autotools (configure) 编译"""
        logger.info("使用 Autotools 编译")
        
        # 查找工具链环境变量
        env_script = self._find_env_script(tools_dir)
        
        if not env_script:
            return {
                "success": False,
                "error": "未找到 HarmonyOS 工具链环境配置脚本",
                "guidance": "需要手动配置交叉编译环境变量",
            }

        # 在 WSL 中执行 configure + make
        configure_cmd = [
            "wsl", "bash", "-c",
            f"cd {project_dir} && source {env_script} && ./configure --prefix={output_dir} {' '.join(extra_args)} && make && make install"
        ]
        
        logger.info(f"配置编译命令: {' '.join(configure_cmd)}")
        
        result = subprocess.run(
            configure_cmd,
            capture_output=True,
            text=True,
            timeout=1800
        )
        
        if result.returncode != 0:
            return {
                "success": False,
                "phase": "configure_build",
                "error": result.stderr.strip() or result.stdout.strip(),
            }

        # 查找生成的 .so 文件
        so_files = self._find_so_files(output_dir)
        
        return {
            "success": True,
            "build_system": "autotools",
            "output_dir": output_dir,
            "so_files": so_files,
            "so_count": len(so_files),
        }

    def _compile_with_gn(
        self, 
        project_dir: str, 
        tools_dir: str, 
        output_dir: str, 
        extra_args: List[str]
    ) -> Dict[str, Any]:
        """使用 GN 编译"""
        logger.info("使用 GN 编译")
        
        # GN 需要工具链文件配置
        toolchain_gn = self._find_toolchain_file(tools_dir, "ohos_toolchain.gn")
        
        if not toolchain_gn:
            return {
                "success": False,
                "error": "未找到 HarmonyOS GN 工具链配置文件",
                "guidance": "请检查 HarmonyOS CommandLine Tools 是否包含 GN 工具链",
            }

        # 执行 gn gen
        gn_cmd = [
            "gn", "gen", output_dir,
            f"--args=toolchain_file=\"{toolchain_gn}\"",
            *extra_args
        ]
        
        logger.info(f"GN配置命令: {' '.join(gn_cmd)}")
        
        gn_result = subprocess.run(
            gn_cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=project_dir
        )
        
        if gn_result.returncode != 0:
            return {
                "success": False,
                "phase": "gn_gen",
                "error": gn_result.stderr.strip() or gn_result.stdout.strip(),
            }

        # 执行 ninja 编译
        ninja_cmd = ["ninja", "-C", output_dir]
        logger.info(f"Ninja编译命令: {' '.join(ninja_cmd)}")
        
        ninja_result = subprocess.run(
            ninja_cmd,
            capture_output=True,
            text=True,
            timeout=1800
        )
        
        if ninja_result.returncode != 0:
            return {
                "success": False,
                "phase": "ninja_build",
                "error": ninja_result.stderr.strip() or ninja_result.stdout.strip(),
            }

        # 查找生成的 .so 文件
        so_files = self._find_so_files(output_dir)
        
        return {
            "success": True,
            "build_system": "gn",
            "output_dir": output_dir,
            "so_files": so_files,
            "so_count": len(so_files),
        }

    def _find_toolchain_file(self, tools_dir: str, filename: str) -> Optional[str]:
        """查找工具链文件"""
        for root, dirs, files in os.walk(tools_dir):
            if filename in files:
                return os.path.join(root, filename)
        return None

    def _find_env_script(self, tools_dir: str) -> Optional[str]:
        """查找环境配置脚本"""
        # 通常是 env.sh 或类似文件
        possible_names = ["env.sh", "setup_env.sh", "harmonyos_env.sh"]
        for name in possible_names:
            script_path = os.path.join(tools_dir, name)
            if os.path.exists(script_path):
                return script_path
        return None

    def _find_so_files(self, directory: str) -> List[str]:
        """递归查找目录下的所有 .so 文件"""
        so_files = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.so') or '.so.' in file:
                    so_files.append(os.path.join(root, file))
        return so_files

    def verify_so_output(self, project_dir: str, output_dir: str = None) -> Dict[str, Any]:
        """
        验证编译输出的 .so 文件

        Args:
            project_dir: 项目目录
            output_dir: 输出目录（可选，默认为 project_dir/build_harmonyos）

        Returns:
            验证结果
        """
        logger.info(f"验证 .so 文件输出: {project_dir}")
        
        # TODO: 实现 .so 文件验证逻辑
        # - 检查文件是否存在
        # - 检查文件大小
        # - 检查文件格式（使用 file 命令）
        # - 检查符号表（使用 nm 或 objdump）
        # - 检查依赖库（使用 ldd 或 readelf）
        
        return {
            "success": True,
            "message": "verify_so_output() 暂未实现，返回占位结果",
            "verified": False,
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
