"""
hilogtool 命令封装

封装 DevEco Studio SDK 中的 hilogtool.exe 工具
用于解析加密的 hilog 日志文件
"""

import os
import subprocess
import tempfile
import shutil
import gzip
from pathlib import Path
from typing import Optional, Dict, Any, List
from loguru import logger

from config import Config, LogSecurityConfig


class HilogtoolWrapper:
    """hilogtool 命令封装类"""
    
    def __init__(self, hilogtool_path: Optional[str] = None):
        """
        初始化 hilogtool 封装
        
        Args:
            hilogtool_path: hilogtool 工具路径，如果为 None 则使用配置中的路径
        """
        self.hilogtool_path = hilogtool_path or Config.HILOGTOOL_PATH
        
        if self.hilogtool_path:
            logger.info(f"初始化 HilogtoolWrapper, 路径: {self.hilogtool_path}")
        else:
            logger.warning("hilogtool 路径未配置")
    
    def is_available(self) -> bool:
        """检查 hilogtool 是否可用"""
        if not self.hilogtool_path:
            return False
        return os.path.isfile(self.hilogtool_path)
    
    def get_version(self) -> Dict[str, Any]:
        """
        获取 hilogtool 版本信息
        
        Returns:
            版本信息字典
        """
        if not self.is_available():
            return {
                'success': False,
                'error': 'hilogtool 不可用'
            }
        
        try:
            result = subprocess.run(
                [self.hilogtool_path, '-v'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            return {
                'success': True,
                'version': result.stdout.strip() or result.stderr.strip(),
                'path': self.hilogtool_path
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': '获取版本超时'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_help(self) -> Dict[str, Any]:
        """
        获取 hilogtool 帮助信息
        
        Returns:
            帮助信息字典
        """
        if not self.is_available():
            return {
                'success': False,
                'error': 'hilogtool 不可用'
            }
        
        try:
            result = subprocess.run(
                [self.hilogtool_path, '-h'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            return {
                'success': True,
                'help': result.stdout + result.stderr,
                'path': self.hilogtool_path
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def parse(
        self,
        input_path: str,
        output_dir: str,
        dict_path: Optional[str] = None,
        timeout: int = 120
    ) -> Dict[str, Any]:
        """
        解析 hilog 日志文件
        
        使用 hilogtool.exe parse 命令解析加密的 hilog 文件
        
        Args:
            input_path: 输入的 hilog 文件或目录路径
            output_dir: 输出目录
            dict_path: 字典文件路径（可选）
            timeout: 超时时间（秒）
            
        Returns:
            解析结果字典
        """
        if not self.is_available():
            return {
                'success': False,
                'error': 'hilogtool 不可用，请检查 HILOGTOOL_PATH 配置'
            }
        
        # 验证输入路径
        if not os.path.exists(input_path):
            return {
                'success': False,
                'error': f'输入路径不存在: {input_path}'
            }
        
        # 验证输出路径
        valid, abs_output = LogSecurityConfig.validate_save_path(output_dir)
        if not valid:
            return {
                'success': False,
                'error': abs_output  # 此时 abs_output 是错误信息
            }
        
        # 确保输出目录存在
        os.makedirs(abs_output, exist_ok=True)
        
        # 构建命令（数组化，防止注入）
        cmd = [
            self.hilogtool_path,
            'parse',
            '-i', input_path,
            '-o', abs_output
        ]
        
        # 如果提供了字典文件
        if dict_path and os.path.exists(dict_path):
            cmd.extend(['-d', dict_path])
        
        logger.info(f"执行 hilogtool parse: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=LogSecurityConfig.validate_timeout(timeout),
                encoding='utf-8',
                errors='replace'
            )
            
            if result.returncode == 0:
                # 获取输出文件列表
                output_files = []
                if os.path.isdir(abs_output):
                    for f in os.listdir(abs_output):
                        file_path = os.path.join(abs_output, f)
                        if os.path.isfile(file_path):
                            output_files.append({
                                'name': f,
                                'path': file_path,
                                'size': os.path.getsize(file_path)
                            })
                
                return {
                    'success': True,
                    'output_dir': abs_output,
                    'output_files': output_files,
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }
            else:
                return {
                    'success': False,
                    'error': f'hilogtool 返回错误码: {result.returncode}',
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': f'hilogtool 执行超时 ({timeout}秒)'
            }
        except Exception as e:
            logger.error(f"hilogtool 执行失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def parse_and_read(
        self,
        input_path: str,
        dict_path: Optional[str] = None,
        max_lines: int = None,
        timeout: int = 120
    ) -> Dict[str, Any]:
        """
        解析 hilog 日志文件并读取内容
        
        Args:
            input_path: 输入的 hilog 文件路径
            dict_path: 字典文件路径（可选）
            max_lines: 最大读取行数
            timeout: 超时时间（秒）
            
        Returns:
            包含解析后日志内容的字典
        """
        if max_lines is None:
            max_lines = LogSecurityConfig.MAX_LOG_LINES
        
        # 创建临时目录
        temp_dir = tempfile.mkdtemp(prefix='hilog_parse_')
        
        try:
            # 解析日志
            parse_result = self.parse(input_path, temp_dir, dict_path, timeout)
            
            if not parse_result['success']:
                return parse_result
            
            # 读取解析后的文件内容
            logs = []
            for file_info in parse_result.get('output_files', []):
                file_path = file_info['path']
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                        for line in f:
                            logs.append(line.rstrip())
                            if len(logs) >= max_lines:
                                break
                except Exception as e:
                    logger.warning(f"读取文件失败 {file_path}: {e}")
                
                if len(logs) >= max_lines:
                    break
            
            truncated = len(logs) >= max_lines
            
            return {
                'success': True,
                'logs': logs,
                'total_lines': len(logs),
                'truncated': truncated,
                'source_file': input_path,
                'dict_used': dict_path is not None
            }
            
        finally:
            # 清理临时目录
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                logger.warning(f"清理临时目录失败: {e}")
    
    def decompress_gz(self, gz_path: str, output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        解压 .gz 格式的 hilog 文件
        
        Args:
            gz_path: .gz 文件路径
            output_path: 输出文件路径（可选，默认去掉 .gz 后缀）
            
        Returns:
            解压结果
        """
        if not os.path.exists(gz_path):
            return {
                'success': False,
                'error': f'文件不存在: {gz_path}'
            }
        
        if not gz_path.endswith('.gz'):
            return {
                'success': False,
                'error': '不是 .gz 文件'
            }
        
        if output_path is None:
            output_path = gz_path[:-3]  # 去掉 .gz 后缀
        
        try:
            with gzip.open(gz_path, 'rb') as f_in:
                with open(output_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            return {
                'success': True,
                'output_path': output_path,
                'size': os.path.getsize(output_path)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


# 全局实例
_hilogtool_wrapper = None


def get_hilogtool_wrapper() -> HilogtoolWrapper:
    """获取 HilogtoolWrapper 单例"""
    global _hilogtool_wrapper
    if _hilogtool_wrapper is None:
        _hilogtool_wrapper = HilogtoolWrapper()
    return _hilogtool_wrapper
