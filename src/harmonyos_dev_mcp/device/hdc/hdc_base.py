"""
Base utilities for the HarmonyOS `hdc` command-line tool.

Provides core command execution helpers and shell command validation.
"""

import asyncio
import os
import subprocess
from typing import Any, Dict, List, Optional

from loguru import logger

from harmonyos_dev_mcp._common.utils.retry import is_transient_error, retry
from harmonyos_dev_mcp.config import Config
from harmonyos_dev_mcp.device.hdc.routing import get_hdc_server_override


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

    @staticmethod
    def _normalize_optional(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    def _effective_hdc_server(self) -> Optional[str]:
        return self._normalize_optional(get_hdc_server_override() or Config.HARMONYOS_HDC_SERVER)

    @staticmethod
    def _server_args(server: Optional[str]) -> List[str]:
        return ["-s", server] if server else []

    @staticmethod
    def _target_args(device_id: Optional[str]) -> List[str]:
        return ["-t", device_id] if device_id else []

    def _hdc_args(
        self,
        args: List[str],
        *,
        device_id: Optional[str] = None,
        hdc_server: Optional[str] = None,
    ) -> List[str]:
        route_ip = self._normalize_optional(hdc_server) or self._effective_hdc_server()
        target = self._normalize_optional(device_id)
        server = None

        if route_ip:
            if target:
                if target != route_ip:
                    server = route_ip
            else:
                target = route_ip

        return self._target_args(target) + self._server_args(server) + args

    def _execute_hdc(
        self,
        args: List[str],
        *,
        device_id: Optional[str] = None,
        timeout: int = None,
        cwd: str = None,
    ) -> Dict[str, Any]:
        command_args = self._hdc_args(args, device_id=device_id)
        if cwd is None:
            return self._execute_command(command_args, timeout=timeout)

        try:
            return self._execute_command(command_args, timeout=timeout, cwd=cwd)
        except TypeError as exc:
            if "cwd" not in str(exc):
                raise
            logger.debug("Falling back to _execute_command without cwd support")
            return self._execute_command(command_args, timeout=timeout)

    async def _execute_hdc_async(
        self,
        args: List[str],
        *,
        device_id: Optional[str] = None,
        timeout: int = None,
        cwd: str = None,
    ) -> Dict[str, Any]:
        return await self._execute_command_async(
            self._hdc_args(args, device_id=device_id),
            timeout=timeout,
            cwd=cwd,
        )

    def _execute_via_tcp(self, args: List[str], timeout: int = None) -> Dict[str, Any]:
        """
        Execute hdc command via direct TCP connection (HarmonyOS mode).

        Bypasses subprocess entirely — connects to hdc server over TCP,
        implements the hdc binary protocol in pure Python.

        Activated when env var HDC_USE_TCP=1 is set.
        """
        from harmonyos_dev_mcp.harmonyos.tcp_hdc import (
            tcp_exec,
            tcp_file_send,
            parse_hdc_args,
        )

        route_ip = self._normalize_optional(self._effective_hdc_server()) or "127.0.0.1:8710"
        parsed = parse_hdc_args(args, route_ip)
        command = parsed["command"]
        connect_key = parsed["connect_key"]

        host = "127.0.0.1"
        port = 8710
        if route_ip and ":" in route_ip:
            parts = route_ip.rsplit(":", 1)
            host = parts[0]
            try:
                port = int(parts[1])
            except ValueError:
                pass

        actual_timeout = timeout or Config.COMMAND_TIMEOUT
        remaining = command.split()

        # file send <local> <remote>
        if len(remaining) >= 4 and remaining[0] == "file" and remaining[1] == "send":
            local_path = remaining[2]
            remote_path = remaining[3]
            out, err, rc = tcp_file_send(
                local_path, remote_path, connect_key, host, port, max(actual_timeout, 120)
            )
            return {"returncode": rc, "stdout": out.strip(), "stderr": err.strip(), "success": rc == 0}

        # file recv <remote> <local>
        if len(remaining) >= 4 and remaining[0] == "file" and remaining[1] == "recv":
            remote_path = remaining[2]
            local_path = remaining[3]
            b64out, _, _ = tcp_exec(f"base64 {remote_path}", connect_key, host, port, 60)
            b64clean = b64out.replace("\n", "").replace("\r", "")
            try:
                import base64 as _b64

                raw = _b64.b64decode(b64clean)
                with open(local_path, "wb") as f:
                    f.write(raw)
                return {
                    "returncode": 0,
                    "stdout": f"recv file ok, size={len(raw)}",
                    "stderr": "",
                    "success": True,
                }
            except Exception as e:
                return {"returncode": 1, "stdout": "", "stderr": str(e), "success": False}

        # install <hap_path> → transfer + bm install
        if len(remaining) >= 2 and remaining[0] == "install":
            hap_path = remaining[-1]
            remote = "/data/local/tmp/_install.hap"
            out, err, rc = tcp_file_send(hap_path, remote, connect_key, host, port, 120)
            if rc != 0:
                return {"returncode": rc, "stdout": "", "stderr": f"transfer failed: {err}", "success": False}
            out, err, rc = tcp_exec(f"bm install -p {remote}", connect_key, host, port, 60)
            tcp_exec(f"rm -f {remote}", connect_key, host, port, 10)
            return {"returncode": rc, "stdout": out.strip(), "stderr": err.strip(), "success": rc == 0}

        # uninstall <bundle>
        if len(remaining) >= 2 and remaining[0] == "uninstall":
            bundle = remaining[-1]
            out, err, rc = tcp_exec(f"bm uninstall -n {bundle}", connect_key, host, port, 30)
            return {"returncode": rc, "stdout": out.strip(), "stderr": err.strip(), "success": rc == 0}

        # General command: shell, list targets, etc.
        out, err, rc = tcp_exec(command, connect_key, host, port, actual_timeout)
        return {"returncode": rc, "stdout": out.strip(), "stderr": err.strip(), "success": rc == 0}

    @retry(should_retry=is_transient_error)
    def _execute_command(self, args: List[str], timeout: int = None, cwd: str = None) -> Dict[str, Any]:
        """
        Execute an `hdc` command synchronously.

        On HarmonyOS (when HDC_USE_TCP=1), uses direct TCP connection
        to hdc server, bypassing subprocess entirely.

        On macOS/Windows (default), uses subprocess.run() as before.

        Args:
            args: Command argument list without the `hdc` executable itself.
            timeout: Timeout in seconds.
            cwd: Optional working directory.

        Returns:
            A result dict with `returncode`, `stdout`, `stderr`, and `success`.
        """
        # HarmonyOS TCP mode: bypass subprocess, connect directly to hdc server
        if os.getenv("HDC_USE_TCP") == "1":
            return self._execute_via_tcp(args, timeout=timeout)

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

        unquoted = self._unquoted_shell_view(stripped)
        for pattern in self.SHELL_DANGEROUS_PATTERNS:
            if pattern in unquoted:
                raise ValueError(f"shell command contains dangerous fragment '{pattern}': {command!r}")

        if "|" in unquoted:
            parts = [part.strip() for part in unquoted.split("|")]
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

    @staticmethod
    def _unquoted_shell_view(command: str) -> str:
        """Hide single-quoted literal text while preserving shell-active content."""
        result: List[str] = []
        state = "plain"
        escaped = False
        for char in command:
            if escaped:
                result.append(char if state != "single" else " ")
                escaped = False
                continue
            if char == "\\" and state != "single":
                result.append(char)
                escaped = True
                continue
            if state == "single":
                if char == "'":
                    state = "plain"
                    result.append(char)
                else:
                    result.append(" ")
                continue
            if state == "double":
                result.append(char)
                if char == '"':
                    state = "plain"
                continue
            result.append(char)
            if char == "'":
                state = "single"
            elif char == '"':
                state = "double"
        return "".join(result)

    def execute_shell(self, device_id: Optional[str], command: str, timeout: int = None) -> Dict[str, Any]:
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
        return self._execute_hdc(["shell", command], device_id=device_id, timeout=timeout)
