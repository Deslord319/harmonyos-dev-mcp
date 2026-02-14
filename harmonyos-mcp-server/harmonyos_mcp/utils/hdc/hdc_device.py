"""
hdc 设备管理模块

提供设备列表、应用安装/卸载等功能。
"""
from typing import List, Dict, Any
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
