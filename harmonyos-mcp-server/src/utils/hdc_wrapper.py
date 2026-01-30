"""
hdc命令行工具封装
"""
import subprocess
import time
import re
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

