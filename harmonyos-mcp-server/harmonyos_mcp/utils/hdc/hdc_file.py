"""
hdc 文件操作模块

提供文件推送/拉取、hilog 文件管理等功能。
"""
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from loguru import logger


class HdcFile:
    """文件操作相关方法"""

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
                timestamp = None
                name_without_gz = filename.rstrip('.gz')
                
                # 尝试多种时间戳提取方式
                if '-' in name_without_gz:
                    time_part = name_without_gz.split('.')[-1]
                    if len(time_part) >= 15 and time_part[0].isdigit():
                        try:
                            timestamp = datetime.strptime(time_part, '%Y%m%d-%H%M%S')
                        except ValueError:
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
    ) -> Dict[str, Any]:
        """
        从设备拉取 hilog 文件到本地
        
        Args:
            device_id: 设备ID
            files: 文件列表（来自 list_hilog_files）
            local_dir: 本地保存目录
        
        Returns:
            拉取结果，包含成功拉取的文件列表
        """
        os.makedirs(local_dir, exist_ok=True)
        
        pulled_files = []
        failed_files = []
        
        for file_info in files:
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
