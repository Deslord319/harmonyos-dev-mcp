"""
hdc 包管理模块

提供包列表、包信息查询、Ability 解析等功能。
"""
import re
import json
from typing import Optional, List, Dict, Any
from loguru import logger


class HdcPackage:
    """包管理相关方法"""

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
        
        # 添加最后一个ability
        if current_ability:
            abilities.append(current_ability)
        
        return abilities

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

    def get_package_permissions(self, device_id: str, bundle_name: str) -> Dict[str, Any]:
        """
        获取指定包的权限信息
        
        Args:
            device_id: 设备ID
            bundle_name: 应用包名
            
        Returns:
            包含权限列表的字典:
            - success: 是否成功
            - bundle_name: 包名
            - requested_permissions: 申请的权限列表
            - permission_count: 权限数量
        """
        logger.debug(f"获取包 {bundle_name} 的权限信息")
        
        # 使用 bm dump -n 获取包详情
        command = f"bm dump -n {bundle_name}"
        result = self.execute_shell(device_id, command)
        
        if not result['success']:
            return {
                'success': False,
                'error': result['stderr'],
                'bundle_name': bundle_name,
                'requested_permissions': [],
                'permission_count': 0
            }
        
        output = result['stdout']
        permissions = []
        
        try:
            # 尝试 JSON 解析
            lines = output.split('\n', 1)
            json_str = lines[1] if len(lines) > 1 and ':' in lines[0] else output
            data = json.loads(json_str)
            
            # 从 reqPermissions 或 requestPermissions 获取
            permissions = data.get('reqPermissions', []) or data.get('requestPermissions', [])
            
            # 如果是字典格式，提取权限名称
            if permissions and isinstance(permissions[0], dict):
                permissions = [p.get('name', '') for p in permissions if p.get('name')]
            
        except json.JSONDecodeError:
            # 文本解析 - 查找 reqPermissions 部分
            for line in output.split('\n'):
                stripped = line.strip()
                if 'permission' in stripped.lower() and ':' in stripped:
                    # 尝试提取权限名称
                    match = re.search(r'"([^"]*permission[^"]*)"', stripped, re.IGNORECASE)
                    if match:
                        permissions.append(match.group(1))
        
        # 去重
        permissions = list(set(permissions))
        
        return {
            'success': True,
            'bundle_name': bundle_name,
            'requested_permissions': sorted(permissions),
            'permission_count': len(permissions)
        }
