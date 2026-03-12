"""UI-related hdc helpers."""

import re
from typing import Any, Dict, Optional

from loguru import logger

from harmonyos_mcp.config import Config


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

        windows = []
        lines = result["stdout"].split("\n")
        header_idx = -1
        for i, line in enumerate(lines):
            if "WindowName" in line and "WinId" in line:
                header_idx = i
                break

        if header_idx == -1:
            logger.warning("Failed to locate window list header")
            return {
                "success": False,
                "error_code": "LIST_WINDOWS_PARSE_ERROR",
                "error": "failed to parse window list header",
                "windows": [],
                "raw_output": result["stdout"],
            }

        pid_bundle_cache: Dict[int, Optional[str]] = {}
        pattern = re.compile(
            r"^(\S+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(-?\d+)\s+(\d+)\s+\[\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*\]"
        )

        for line in lines[header_idx + 1 :]:
            line = line.strip()
            if not line or line.startswith("-"):
                continue

            match = pattern.match(line)
            if not match:
                continue

            try:
                pid = int(match.group(3))
                zord = int(match.group(8))
                if pid not in pid_bundle_cache:
                    pid_bundle_cache[pid] = self.get_bundle_name_by_pid(device_id, pid)
                windows.append(
                    {
                        "window_name": match.group(1),
                        "display_id": int(match.group(2)),
                        "pid": pid,
                        "window_id": int(match.group(4)),
                        "type": int(match.group(5)),
                        "mode": int(match.group(6)),
                        "flag": int(match.group(7)),
                        "zord": zord,
                        "bundle_name": pid_bundle_cache.get(pid) or "",
                        "orient": int(match.group(9)),
                        "rect": {
                            "x": int(match.group(10)),
                            "y": int(match.group(11)),
                            "w": int(match.group(12)),
                            "h": int(match.group(13)),
                        },
                        "is_visible": zord > 0,
                    }
                )
            except (ValueError, IndexError) as exc:
                logger.debug(f"Failed to parse window line: {line}, error: {exc}")

        if result["stdout"].strip() and not windows:
            logger.warning("Window list command returned output but no windows were parsed")
            return {
                "success": False,
                "error_code": "LIST_WINDOWS_PARSE_ERROR",
                "error": "failed to parse any windows from output",
                "windows": [],
                "raw_output": result["stdout"],
            }

        logger.info(f"Found {len(windows)} windows")
        return {
            "success": True,
            "windows": windows,
            "count": len(windows),
        }

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
        logger.info(f"Finding window for bundle {bundle_name}")
        window_list = self.get_window_list(device_id)

        if not window_list["success"]:
            logger.error("Failed to get window list")
            return None

        target_bundle = bundle_name.strip()
        for window in window_list["windows"]:
            if window.get("bundle_name") == target_bundle and window.get("is_visible"):
                logger.info(f"Matched visible window {window['window_name']} ({window['window_id']})")
                return window["window_id"]

        for window in window_list["windows"]:
            if window.get("bundle_name") == target_bundle:
                logger.info(f"Matched background window {window['window_name']} ({window['window_id']})")
                return window["window_id"]

        logger.warning(f"Window not found for bundle {bundle_name}")
        return None
