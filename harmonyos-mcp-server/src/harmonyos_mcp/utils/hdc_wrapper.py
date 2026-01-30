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

    def start_app(self, device_id: str, bundle_name: str, ability_name: str = "EntryAbility", module_name: str = "entry") -> bool:
        """
        启动应用

        Args:
            device_id: 设备ID
            bundle_name: 应用包名
            ability_name: Ability名称
            module_name: 模块名称

        Returns:
            是否启动成功
        """
        logger.info(f"启动应用: {bundle_name}/{ability_name} (module: {module_name})")

        # 使用aa start命令启动应用，添加-m参数指定模块
        command = f"aa start -a {ability_name} -b {bundle_name} -m {module_name}"
        result = self.execute_shell(device_id, command)

        if result['success']:
            logger.info(f"应用启动成功")
            return True
        else:
            logger.error(f"应用启动失败: {result['stderr']}")
            return False

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
        for line in lines[header_idx + 1:]:
            line = line.strip()
            if not line:
                continue

            # 使用正则表达式解析窗口信息
            # 格式: WindowName DisplayId PID WinId Type Mode Flag Orient FirstFrame IsVisible ...
            parts = line.split()
            if len(parts) >= 10:
                try:
                    window_info = {
                        'window_name': parts[0],
                        'display_id': int(parts[1]),
                        'pid': int(parts[2]),
                        'window_id': int(parts[3]),
                        'type': int(parts[4]),
                        'mode': int(parts[5]),
                        'flag': int(parts[6]),
                        'orient': int(parts[7]),
                        'first_frame': int(parts[8]),
                        'is_visible': parts[9].lower() == 'true'
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

    def get_ui_tree_raw(self, device_id: str, window_id: int) -> Dict[str, Any]:
        """
        获取指定窗口的UI组件树原始输出（使用 -inspector 参数获取屏幕绝对坐标）

        Args:
            device_id: 设备ID
            window_id: 窗口ID

        Returns:
            包含UI组件树原始文本的字典
        """
        logger.info(f"获取窗口 {window_id} 的UI组件树")
        # 使用 -inspector 参数，返回的坐标是屏幕绝对坐标，可直接用于点击操作
        command = f"hidumper -s WindowManagerService -a '-w {window_id} -inspector'"
        result = self.execute_shell(device_id, command)

        if not result['success']:
            logger.error(f"获取UI组件树失败: {result['stderr']}")
            return {
                'success': False,
                'error': result['stderr'],
                'ui_tree': ''
            }

        logger.info(f"成功获取UI组件树，输出长度: {len(result['stdout'])} 字符")
        return {
            'success': True,
            'window_id': window_id,
            'ui_tree': result['stdout']
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

        # 查找匹配的窗口
        for window in window_list['windows']:
            window_name = window['window_name'].lower()
            # 窗口名称通常包含应用名或包名的一部分
            if bundle_name.lower() in window_name or window_name in bundle_name.lower():
                logger.info(f"找到匹配窗口: {window['window_name']}, ID: {window['window_id']}")
                return window['window_id']

        # 如果没有找到精确匹配，返回第一个可见窗口
        for window in window_list['windows']:
            if window['is_visible']:
                logger.info(f"使用第一个可见窗口: {window['window_name']}, ID: {window['window_id']}")
                return window['window_id']

        logger.warning(f"未找到应用 {bundle_name} 的窗口")
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

    def clone_library(self, repo_url: str, local_path: str) -> Dict[str, Any]:
        """
        拉取三方库代码仓库

        Args:
            repo_url: 仓库 URL (git/https)
            local_path: 本地存放路径

        Returns:
            拉取结果
        """
        logger.info(f"开始拉取三方库: {repo_url} -> {local_path}")
        
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
            result = subprocess.run(
                ["git", "clone", repo_url, local_path],
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
