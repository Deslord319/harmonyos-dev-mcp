"""
hdc device helpers.

Provides device listing, device info, install and uninstall operations.
"""

import re
from typing import Any, Dict, List

from loguru import logger

from harmonyos_dev_mcp.config import Config


class HdcDevice:
    """Device-related hdc operations."""

    INSTALL_FAILURE_PATTERN = re.compile(
        r"(?im)(?:\[(?:install_failed)\]|(?:^|\b)install\s+(?:bundle\s+)?failed\b|\bfailed\s+to\s+install\b)"
    )
    UNINSTALL_FAILURE_PATTERN = re.compile(
        r"(?im)(?:\[(?:uninstall_failed)\]|(?:^|\b)uninstall\s+failed\b|\bfailed\s+to\s+uninstall\b)"
    )

    @staticmethod
    def _extract_action_error(result: Dict[str, Any], fallback: str) -> str:
        for key in ("stderr", "stdout"):
            value = (result.get(key) or "").strip()
            if value:
                return value
        return fallback

    @staticmethod
    def _looks_like_install_failure(output: str) -> bool:
        return bool(HdcDevice.INSTALL_FAILURE_PATTERN.search(output or ""))

    @staticmethod
    def _looks_like_uninstall_failure(output: str) -> bool:
        return bool(HdcDevice.UNINSTALL_FAILURE_PATTERN.search(output or ""))

    def list_devices(self) -> List[str]:
        """Return connected device ids."""
        logger.debug("Getting device list")
        result = self._execute_command(["list", "targets"])

        if not result["success"]:
            logger.error(f"Failed to list devices: {result['stderr']}")
            return []

        devices = [line.strip() for line in result["stdout"].split("\n") if line.strip()]
        logger.debug(f"Found {len(devices)} devices: {devices}")
        return devices

    def get_device_info(self, device_id: str) -> Dict[str, Any]:
        """Return device information such as model and OS version."""
        logger.debug(f"Getting details for device {device_id}")

        props = {
            "model": "const.product.model",
            "device_name": "const.product.name",
            "os_version": "const.ohos.fullname",
            "api_version": "const.ohos.apiversion",
        }

        info = {"device_id": device_id}

        for key, prop in props.items():
            result = self.execute_shell(device_id, f"param get {prop}")
            if result["success"]:
                stdout = result["stdout"].strip()
                if stdout and "fail" not in stdout.lower() and "errNum" not in stdout:
                    info[key] = stdout

        wm_result = self.execute_shell(device_id, "hidumper -s WindowManagerService -a '-a'")
        if wm_result["success"]:
            output = wm_result["stdout"]
            import re

            match = re.search(r"\[\s*\d+\s+\d+\s+(\d+)\s+(\d+)\s*\]", output)
            if match:
                width, height = match.groups()
                info["screen_size"] = f"{width}x{height}"

        return info

    def list_devices_with_info(self) -> List[Dict[str, Any]]:
        """Return connected devices with extra metadata."""
        return [self.get_device_info(device_id) for device_id in self.list_devices()]

    def install_app(self, device_id: str, hap_path: str) -> Dict[str, Any]:
        """Install a hap on the target device."""
        from pathlib import Path

        hap_file = Path(hap_path).resolve()
        hap_dir = str(hap_file.parent)
        hap_name = hap_file.name

        logger.info(f"Installing app on {device_id}: {hap_file} (cwd={hap_dir})")
        result = self._execute_command(
            ["-t", device_id, "install", hap_name],
            timeout=Config.INSTALL_TIMEOUT,
            cwd=hap_dir,
        )

        combined_output = "\n".join(
            part
            for part in ((result.get("stdout") or "").strip(), (result.get("stderr") or "").strip())
            if part
        )
        command_success = bool(result.get("success"))
        success = command_success and not self._looks_like_install_failure(combined_output)

        payload = dict(result)
        payload.update(
            {
                "success": success,
                "device_id": device_id,
                "hap_path": hap_path,
            }
        )

        if success:
            logger.info("App install succeeded")
        else:
            payload["error_code"] = "INSTALL_FAILED"
            payload["error"] = self._extract_action_error(payload, "install app failed")
            logger.error(f"App install failed: {payload['error']}")

        return payload

    def uninstall_app(self, device_id: str, bundle_name: str) -> Dict[str, Any]:
        """Uninstall an app from the target device."""
        logger.info(f"Uninstalling app from {device_id}: {bundle_name}")
        result = self._execute_command(["-t", device_id, "uninstall", bundle_name])

        combined_output = "\n".join(
            part
            for part in ((result.get("stdout") or "").strip(), (result.get("stderr") or "").strip())
            if part
        )
        command_success = bool(result.get("success"))
        success = command_success and not self._looks_like_uninstall_failure(combined_output)

        payload = dict(result)
        payload.update(
            {
                "success": success,
                "device_id": device_id,
                "bundle_name": bundle_name,
            }
        )

        if success:
            logger.info("App uninstall succeeded")
        else:
            payload["error_code"] = "UNINSTALL_FAILED"
            payload["error"] = self._extract_action_error(payload, "uninstall app failed")
            logger.error(f"App uninstall failed: {payload['error']}")

        return payload
