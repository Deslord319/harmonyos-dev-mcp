"""UI-related hdc helpers."""

from typing import Any, Dict, Optional

from loguru import logger

from harmonyos_dev_mcp.config import Config
from harmonyos_dev_mcp.utils.parsers.window_manager import parse_window_list_output
from harmonyos_dev_mcp.utils.selectors.window_selector import resolve_window_target as select_window_target


class HdcUI:
    """UI and window inspection helpers."""

    def get_window_list(self, device_id: str) -> Dict[str, Any]:
        logger.info(f"Getting window list for device {device_id}")
        command = "hidumper -s WindowManagerService -a '-a'"
        result = self.execute_shell(device_id, command)

        if not result["success"]:
            logger.error(f"Failed to get window list: {result['stderr']}")
            return {
                "success": False,
                "error": result["stderr"],
                "windows": [],
            }

        parsed = parse_window_list_output(
            result["stdout"],
            resolve_bundle_name=lambda pid: self.get_bundle_name_by_pid(device_id, pid),
        )
        if not parsed.get("success", False):
            logger.warning(parsed.get("error", "failed to parse window list"))
            return parsed

        logger.info(f"Found {parsed['count']} windows")
        return parsed

    def get_ui_tree_raw(self, device_id: str, window_id: int = None) -> Dict[str, Any]:
        timeout = Config.UI_TREE_TIMEOUT
        logger.info(f"Getting UI tree (device={device_id}, timeout={timeout}s, window_id={window_id})")

        dump_result = self.execute_shell(device_id, "uitest dumpLayout", timeout=timeout)
        if not dump_result["success"]:
            logger.error(f"uitest dumpLayout failed: {dump_result['stderr']}")
            return {
                "success": False,
                "error": dump_result["stderr"],
                "ui_tree": "",
            }

        output = dump_result["stdout"].strip()
        if "saved to:" not in output:
            logger.error(f"Unable to parse dumpLayout output: {output}")
            return {
                "success": False,
                "error": f"unable to parse dumpLayout output: {output}",
                "ui_tree": "",
            }

        json_path = output.split("saved to:")[-1].strip()
        logger.info(f"UI tree saved at: {json_path}")

        cat_result = self.execute_shell(device_id, f"cat {json_path}", timeout=timeout)
        if not cat_result["success"]:
            logger.error(f"Failed to read UI tree file: {cat_result['stderr']}")
            return {
                "success": False,
                "error": cat_result["stderr"],
                "ui_tree": "",
            }

        return {
            "success": True,
            "window_id": window_id,
            "ui_tree": cat_result["stdout"],
            "format": "uitest_json",
        }

    def find_window_by_bundle(self, device_id: str, bundle_name: str) -> Optional[int]:
        resolved = self.resolve_window_target(device_id, bundle_name=bundle_name)
        if not resolved.get("success", False):
            logger.warning(f"Window not found for bundle {bundle_name}")
            return None
        window = resolved.get("window")
        return window.get("window_id") if isinstance(window, dict) else None

    def resolve_window_target(
        self,
        device_id: str,
        *,
        bundle_name: Optional[str] = None,
        window_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        window_list = self.get_window_list(device_id)
        if not window_list.get("success", False):
            return {
                "success": False,
                "error_code": window_list.get("error_code", "LIST_WINDOWS_ERROR"),
                "error": window_list.get("error", "failed to list windows"),
                "window": None,
                "windows": [],
            }

        windows = window_list.get("windows", [])
        return select_window_target(
            windows,
            bundle_name=bundle_name,
            window_id=window_id,
        )
