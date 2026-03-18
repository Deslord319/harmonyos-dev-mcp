"""Application-level hdc helpers."""

import time
from typing import Any, Dict, Optional

from loguru import logger


class HdcApp:
    """Application and process helpers."""

    PID_BUNDLE_CACHE_TTL_SECONDS = 3.0

    @staticmethod
    def _normalize_bundle_from_process_name(process_name: str) -> str:
        normalized = (process_name or "").strip().strip("\x00")
        if not normalized:
            return ""
        first_token = normalized.replace("\x00", " ").split()[0]
        return first_token.split(":", 1)[0]

    def _get_pid_bundle_cache(self) -> dict[tuple[str, int], tuple[float, Optional[str]]]:
        cache = getattr(self, "_pid_bundle_cache", None)
        if cache is None:
            cache = {}
            self._pid_bundle_cache = cache
        return cache

    def _prune_pid_bundle_cache(self, now: float) -> None:
        cache = self._get_pid_bundle_cache()
        expired_keys = [key for key, (expires_at, _) in cache.items() if expires_at <= now]
        for key in expired_keys:
            cache.pop(key, None)

    def get_bundle_name_by_pid(self, device_id: str, pid: int) -> Optional[str]:
        logger.debug(f"Resolving bundle name for pid {pid}")
        now = time.monotonic()
        cache_key = (device_id, pid)
        cache = self._get_pid_bundle_cache()
        self._prune_pid_bundle_cache(now)

        cached = cache.get(cache_key)
        if cached is not None:
            _, cached_bundle = cached
            cache[cache_key] = (now + self.PID_BUNDLE_CACHE_TTL_SECONDS, cached_bundle)
            logger.debug(f"PID bundle cache hit for {cache_key}: {cached_bundle}")
            return cached_bundle

        result = self.execute_shell(device_id, f"cat /proc/{pid}/cmdline")
        if result["success"] and result["stdout"]:
            bundle_name = self._normalize_bundle_from_process_name(result["stdout"])
            if bundle_name:
                logger.info(f"Resolved pid {pid} to bundle {bundle_name}")
                cache[cache_key] = (time.monotonic() + self.PID_BUNDLE_CACHE_TTL_SECONDS, bundle_name)
                return bundle_name

        ps_result = self.execute_shell(device_id, f"ps -A | grep {pid}")
        if ps_result["success"] and ps_result["stdout"]:
            for line in ps_result["stdout"].splitlines():
                tokens = line.split()
                if not tokens or str(pid) not in tokens:
                    continue
                bundle_name = self._normalize_bundle_from_process_name(tokens[-1])
                if bundle_name:
                    logger.info(f"Resolved pid {pid} to bundle {bundle_name} via ps")
                    cache[cache_key] = (time.monotonic() + self.PID_BUNDLE_CACHE_TTL_SECONDS, bundle_name)
                    return bundle_name

        logger.warning(f"Unable to resolve bundle name for pid {pid}")
        cache[cache_key] = (time.monotonic() + self.PID_BUNDLE_CACHE_TTL_SECONDS, None)
        return None

    def get_app_pid(self, device_id: str, package_name: str) -> Optional[int]:
        logger.debug(f"Getting pid for package {package_name}")
        result = self.execute_shell(device_id, f"pidof {package_name}")

        if result["success"] and result["stdout"].strip():
            try:
                pid_str = result["stdout"].strip().split()[0]
                pid = int(pid_str)
                logger.info(f"Package {package_name} pid: {pid}")
                return pid
            except (ValueError, IndexError):
                logger.warning(f"Unable to parse pid from: {result['stdout']}")
                return None

        logger.debug(f"Package {package_name} is not running")
        return None

    def start_app(
        self,
        device_id: str,
        bundle_name: str,
        ability_name: str = "EntryAbility",
        module_name: str = "entry",
        verify: bool = True,
        timeout: float = 3.0,
    ) -> Dict[str, Any]:
        logger.info(f"Starting app: {bundle_name}/{ability_name} (module={module_name})")
        command = f"aa start -a {ability_name} -b {bundle_name} -m {module_name}"
        result = self.execute_shell(device_id, command)

        if not result["success"]:
            logger.error(f"App start command failed: {result['stderr']}")
            return {
                "success": False,
                "error": result["stderr"],
                "command_success": False,
                "window_found": False,
            }

        if not verify:
            return {
                "success": True,
                "command_success": True,
                "window_found": None,
                "message": "start command executed without window verification",
            }

        start_time = time.time()
        window_found = False
        window_info = None

        while time.time() - start_time < timeout:
            resolved = self.resolve_window_target(device_id, bundle_name=bundle_name)
            if resolved.get("success", False):
                window = resolved.get("window")
                if isinstance(window, dict) and window.get("is_visible"):
                    window_found = True
                    window_info = {
                        "window_name": window["window_name"],
                        "window_id": window["window_id"],
                        "zord": window.get("zord"),
                        "rect": window.get("rect"),
                    }
            if window_found:
                break
            time.sleep(0.3)

        if window_found:
            logger.info(f"App started and visible window detected: {window_info['window_name']}")
            return {
                "success": True,
                "command_success": True,
                "window_found": True,
                "window": window_info,
            }

        logger.warning(f"Start command succeeded but window was not detected for {bundle_name}")
        return {
            "success": False,
            "error": "app window did not appear after start command",
            "command_success": True,
            "window_found": False,
        }

    def forward_port(self, device_id: str, local_port: int, remote_port: int) -> bool:
        logger.info(f"Forwarding localhost:{local_port} -> device:{remote_port}")
        result = self._execute_command(
            ["-t", device_id, "fport", f"tcp:{local_port}", f"tcp:{remote_port}"]
        )

        if result["success"]:
            logger.info("Port forwarding configured")
            return True

        logger.error(f"Port forwarding failed: {result['stderr']}")
        return False
