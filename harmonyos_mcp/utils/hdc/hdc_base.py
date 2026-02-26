"""
hdc 命令行工具基础类

提供核心命令执行和 shell 命令校验功能。
"""
import asyncio
import subprocess
from typing import List, Optional, Dict, Any
from loguru import logger

from harmonyos_mcp.config import Config
from harmonyos_mcp.utils.retry import retry, is_transient_hdc_failure


class HdcBase:
    """HarmonyOS Device Connector (hdc) 工具基础类"""

    # Shell 命令白名单：仅允许执行以下命令
    SHELL_COMMAND_WHITELIST = [
        'ls', 'cat', 'pidof', 'ps', 'cp', 'rm', 'mkdir',
        'hilog', 'bm', 'aa', 'param', 'dumpsys', 'hidumper',
        'uitest', 'snapshot_display', 'power-shell',
        'getprop', 'settings', 'wm', 'input',
        'chmod', 'chown', 'stat', 'df', 'du',
        'echo', 'grep', 'find', 'head', 'tail', 'wc',
        'date', 'id', 'whoami', 'uname',
    ]

    # 危险字符模式：禁止命令中包含以下字符序列
    SHELL_DANGEROUS_PATTERNS = ['&&', '||', '`', '$(', ';', '\\n', '\\r', '$((', '|}']

    # 禁止的危险命令（即使在白名单中也不允许）
    SHELL_COMMAND_BLACKLIST = [
        'base64', 'tar', 'zip', 'unzip', 'gzip', 'gunzip', 'bzip2', 'xz',
        'wget', 'curl', 'nc', 'netcat', 'ncat', 'socat',
        'python', 'python3', 'perl', 'ruby', 'php', 'node',
        'bash', 'sh', 'dash', 'ash', 'zsh',
        'chsh', 'passwd', 'su', 'sudo', 'login',
        'dd', 'mkfs', 'fdisk', 'parted',
        'reboot', 'shutdown', 'poweroff', 'halt',
        'iptables', 'ufw', 'firewall-cmd',
        'mount', 'umount', 'losetup',
    ]

    # 管道操作仅允许以下命令
    PIPE_ALLOWED_COMMANDS = ['ls', 'ps', 'cat', 'grep', 'hilog', 'dumpsys']

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
            except Exception as kill_err:
                logger.warning(f"终止超时进程失败: {kill_err}")
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

    def _validate_shell_command(self, command: str) -> None:
        """
        校验 shell 命令安全性
        
        检查：
        1. 命令是否在白名单中
        2. 是否包含危险字符（&&, ||, ``, $() 等）
        3. 管道操作是否合法
        
        Args:
            command: 待校验的 shell 命令
            
        Raises:
            ValueError: 命令不合法时
        """
        stripped = command.strip()
        if not stripped:
            raise ValueError("Shell 命令不能为空")
        
        # 检查危险模式
        for pattern in self.SHELL_DANGEROUS_PATTERNS:
            if pattern in stripped:
                raise ValueError(
                    f"Shell 命令包含危险字符 '{pattern}': {command!r}"
                )
        
        # 检查管道
        if '|' in stripped:
            parts = [p.strip() for p in stripped.split('|')]
            for part in parts:
                cmd_name = part.split()[0] if part.split() else ''
                if cmd_name not in self.PIPE_ALLOWED_COMMANDS:
                    raise ValueError(
                        f"管道命令 '{cmd_name}' 不在允许列表中: {self.PIPE_ALLOWED_COMMANDS}"
                    )
            return
        
        # 提取主命令（处理 2>/dev/null 等重定向）
        cmd_name = stripped.split()[0]

        # 检查黑名单
        if hasattr(self, 'SHELL_COMMAND_BLACKLIST') and cmd_name in self.SHELL_COMMAND_BLACKLIST:
            raise ValueError(f"Shell 命令 '{cmd_name}' 被禁止执行")

        if cmd_name not in self.SHELL_COMMAND_WHITELIST:
            raise ValueError(
                f"Shell 命令 '{cmd_name}' 不在白名单中。"
                f"允许的命令: {self.SHELL_COMMAND_WHITELIST}"
            )

    def execute_shell(self, device_id: str, command: str, timeout: int = None) -> Dict[str, Any]:
        """
        在设备上执行Shell命令（带白名单校验）

        Args:
            device_id: 设备ID
            command: Shell命令
            timeout: 超时时间(秒)，默认使用 COMMAND_TIMEOUT

        Returns:
            命令执行结果
        """
        # 安全校验
        self._validate_shell_command(command)

        logger.debug(f"在设备 {device_id} 上执行Shell命令: {command}" + (f", 超时: {timeout}s" if timeout else ""))
        result = self._execute_command(['-t', device_id, 'shell', command], timeout=timeout)
        return result
