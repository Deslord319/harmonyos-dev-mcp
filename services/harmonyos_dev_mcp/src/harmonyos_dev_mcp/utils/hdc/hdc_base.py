"""
Base utilities for the HarmonyOS `hdc` command-line tool.

Provides core command execution helpers and shell command validation.
"""

import asyncio
import subprocess
from typing import Any, Dict, List, Optional

from loguru import logger

from common.utils.retry import is_transient_error, retry
from harmonyos_dev_mcp.config import Config


class HdcBase:
    """Base wrapper for HarmonyOS Device Connector (`hdc`)."""

    # Shell command allowlist.
    SHELL_COMMAND_WHITELIST = [
        "ls",
        "cat",
        "pidof",
        "ps",
        "cp",
        "rm",
        "mkdir",
        "hilog",
        "bm",
        "aa",
        "param",
        "dumpsys",
        "hidumper",
        "uitest",
        "snapshot_display",
        "power-shell",
        "getprop",
        "settings",
        "wm",
        "input",
        "chmod",
        "chown",
        "stat",
        "df",
        "du",
        "echo",
        "grep",
        "find",
        "head",
        "tail",
        "wc",
        "date",
        "id",
        "whoami",
        "uname",
    ]

    # Dangerous shell fragments that are not allowed.
    SHELL_DANGEROUS_PATTERNS = ["&&", "||", "`", "$(", ";", "\\n", "\\r", "$((", "|}"]

    # Explicitly forbidden commands, even if they would otherwise look harmless.
    SHELL_COMMAND_BLACKLIST = [
        "base64",
        "tar",
        "zip",
        "unzip",
        "gzip",
        "gunzip",
        "bzip2",
        "xz",
        "wget",
        "curl",
        "nc",
        "netcat",
        "ncat",
        "socat",
        "python",
        "python3",
        "perl",
        "ruby",
        "php",
        "node",
        "bash",
        "sh",
        "dash",
        "ash",
        "zsh",
        "chsh",
        "passwd",
        "su",
        "sudo",
        "login",
        "dd",
        "mkfs",
        "fdisk",
        "parted",
        "reboot",
        "shutdown",
        "poweroff",
        "halt",
        "iptables",
        "ufw",
        "firewall-cmd",
        "mount",
        "umount",
        "losetup",
    ]

    # Only these commands may appear in pipe chains.
    PIPE_ALLOWED_COMMANDS = ["ls", "ps", "cat", "grep", "hilog", "dumpsys"]

    def __init__(self, hdc_path: Optional[str] = None):
        """
        Initialize the hdc wrapper.

        Args:
            hdc_path: Path to the `hdc` executable. If omitted, use config.
        """
        Config.ensure_init()
        self.hdc_path = hdc_path or Config.HDC_PATH
        if not self.hdc_path:
            raise ValueError("hdc tool path is not configured")

        logger.info(f"Initialized HdcWrapper, hdc path: {self.hdc_path}")

    @retry(should_retry=is_transient_error)
    def _execute_command(self, args: List[str], timeout: int = None, cwd: str = None) -> Dict[str, Any]:
        """
        Execute an `hdc` command synchronously.

        Args:
            args: Command argument list without the `hdc` executable itself.
            timeout: Timeout in seconds.
            cwd: Optional working directory.

        Returns:
            A result dict with `returncode`, `stdout`, `stderr`, and `success`.
        """
        cmd = [self.hdc_path] + args
        timeout = timeout or Config.COMMAND_TIMEOUT

        logger.debug(f"Executing command: {' '.join(cmd)} (cwd={cwd or 'default'})")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="ignore",
                cwd=cwd,
            )

            return {
                "returncode": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "success": result.returncode == 0,
            }
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {' '.join(cmd)}")
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": f"command timed out ({timeout}s)",
                "success": False,
            }
        except Exception as exc:
            logger.error(f"Command execution failed: {exc}")
            return {"returncode": -1, "stdout": "", "stderr": str(exc), "success": False}

    async def _execute_command_async(self, args: List[str], timeout: int = None, cwd: str = None) -> Dict[str, Any]:
        """
        Execute an `hdc` command asynchronously.

        Args:
            args: Command argument list without the `hdc` executable itself.
            timeout: Timeout in seconds.
            cwd: Optional working directory.

        Returns:
            A result dict with `returncode`, `stdout`, `stderr`, and `success`.
        """
        cmd = [self.hdc_path] + args
        timeout = timeout or Config.COMMAND_TIMEOUT

        logger.debug(f"Executing command asynchronously: {' '.join(cmd)} (cwd={cwd or 'default'})")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=timeout)

            return {
                "returncode": process.returncode,
                "stdout": stdout_bytes.decode("utf-8", errors="ignore").strip(),
                "stderr": stderr_bytes.decode("utf-8", errors="ignore").strip(),
                "success": process.returncode == 0,
            }
        except asyncio.TimeoutError:
            logger.error(f"Async command timed out: {' '.join(cmd)}")
            try:
                process.kill()
                await process.wait()
            except Exception as kill_err:
                logger.warning(f"Failed to terminate timed out process: {kill_err}")
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": f"command timed out ({timeout}s)",
                "success": False,
            }
        except Exception as exc:
            logger.error(f"Async command execution failed: {exc}")
            return {"returncode": -1, "stdout": "", "stderr": str(exc), "success": False}

    def _validate_shell_command(self, command: str) -> None:
        """
        Validate shell command safety.

        Checks:
        1. Command is not empty.
        2. Command does not contain dangerous shell fragments.
        3. Pipe chains only use allowed commands.
        4. Top-level command is allowed and not blacklisted.

        Args:
            command: Shell command to validate.

        Raises:
            ValueError: If the command is not allowed.
        """
        stripped = command.strip()
        if not stripped:
            raise ValueError("shell command cannot be empty")

        for pattern in self.SHELL_DANGEROUS_PATTERNS:
            if pattern in stripped:
                raise ValueError(f"shell command contains dangerous fragment '{pattern}': {command!r}")

        if "|" in stripped:
            parts = [part.strip() for part in stripped.split("|")]
            for part in parts:
                cmd_name = part.split()[0] if part.split() else ""
                if cmd_name not in self.PIPE_ALLOWED_COMMANDS:
                    raise ValueError(
                        f"pipe command '{cmd_name}' is not allowed: {self.PIPE_ALLOWED_COMMANDS}"
                    )
            return

        cmd_name = stripped.split()[0]

        if cmd_name in self.SHELL_COMMAND_BLACKLIST:
            raise ValueError(f"shell command '{cmd_name}' is forbidden")

        if cmd_name not in self.SHELL_COMMAND_WHITELIST:
            raise ValueError(
                f"shell command '{cmd_name}' is not in the allowlist: {self.SHELL_COMMAND_WHITELIST}"
            )

    def execute_shell(self, device_id: str, command: str, timeout: int = None) -> Dict[str, Any]:
        """
        Execute a validated shell command on a device.

        Args:
            device_id: Target device ID.
            command: Shell command to execute.
            timeout: Optional timeout in seconds.

        Returns:
            Command execution result.
        """
        self._validate_shell_command(command)

        logger.debug(
            f"Executing shell command on device {device_id}: {command}"
            + (f", timeout={timeout}s" if timeout else "")
        )
        return self._execute_command(["-t", device_id, "shell", command], timeout=timeout)
