"""
hdc 设备管理模块

提供设备列表、应用安装/卸载等功能。
"""
from typing import List, Dict, Any, Optional
from loguru import logger

from harmonyos_mcp.config import Config


class HdcDevice:
    """设备管理相关方法"""

    def list_devices(self) -> List[str]:
        """
        列出所有连接的设备
        
        Returns:
            设备ID列表
        """
        logger.debug("获取设备列表")
        result = self._execute_command(['list', 'targets'])
        
        if not result['success']:
            logger.error(f"获取设备列表失败: {result['stderr']}")
            return []
        
        devices = [line.strip() for line in result['stdout'].split('\n') if line.strip()]
        logger.debug(f"找到 {len(devices)} 个设备: {devices}")
        return devices

    def get_device_info(self, device_id: str) -> Dict[str, Any]:
        """
        获取设备详细信息（型号、系统版本等）
        
        Args:
            device_id: 设备ID
            
        Returns:
            设备信息字典
        """
        logger.debug(f"获取设备 {device_id} 的详细信息")
        
        # HarmonyOS 使用 param get 命令（而非 Android 的 getprop）
        props = {
            'model': 'const.product.model',
            'device_name': 'const.product.name',
            'os_version': 'const.ohos.fullname',
            'api_version': 'const.ohos.apiversion',
        }
        
        info = {'device_id': device_id}
        
        for key, prop in props.items():
            result = self.execute_shell(device_id, f'param get {prop}')
            if result['success']:
                stdout = result['stdout'].strip()
                # 检查是否为错误响应（HarmonyOS 错误格式：Get parameter "xxx" fail!）
                if stdout and 'fail' not in stdout.lower() and 'errNum' not in stdout:
                    info[key] = stdout
        
        # 获取屏幕分辨率（从 WindowManagerService 解析）
        wm_result = self.execute_shell(device_id, 'hidumper -s WindowManagerService -a \'-a\'')
        if wm_result['success']:
            output = wm_result['stdout']
            # 解析格式: [ x    y    w    h    ]
            # 查找第一个窗口的分辨率信息
            import re
            match = re.search(r'\[\s*\d+\s+\d+\s+(\d+)\s+(\d+)\s*\]', output)
            if match:
                width, height = match.groups()
                info['screen_size'] = f'{width}x{height}'
        
        return info

    def list_devices_with_info(self) -> List[Dict[str, Any]]:
        """
        列出所有设备及其详细信息
        
        Returns:
            设备信息列表
        """
        devices = self.list_devices()
        result = []
        
        for device_id in devices:
            info = self.get_device_info(device_id)
            result.append(info)
        
        return result

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
