"""UI-related hdc helpers."""

import re
from typing import Any, Dict, Optional

from loguru import logger

from harmonyos_mcp.config import Config
from harmonyos_mcp.utils.ui_common import normalize_bundle_name


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

        pid_bundle_cache: Dict[int, Optional[str]] = {}
        pattern = re.compile(
            r"^(\S+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(-?\d+)\s+(\d+)\s+\[\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*\]"
        )

        candidate_lines = lines[header_idx + 1 :] if header_idx != -1 else lines
        for line in candidate_lines:
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

        if header_idx == -1 and windows:
            logger.warning("Window list header not found, using regex-only parse fallback")

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
        if not windows:
            return {
                "success": False,
                "error_code": "NO_WINDOWS",
                "error": "no window found",
                "window": None,
                "windows": [],
            }

        target_bundle = normalize_bundle_name(bundle_name)
        matched_window: Optional[Dict[str, Any]] = None

        if window_id is not None:
            matched_window = next((w for w in windows if w.get("window_id") == window_id), None)
            if not matched_window:
                return {
                    "success": False,
                    "error_code": "WINDOW_NOT_FOUND",
                    "error": f"window not found: {window_id}",
                    "window": None,
                    "windows": windows,
                }
            if target_bundle and normalize_bundle_name(matched_window.get("bundle_name")) != target_bundle:
                return {
                    "success": False,
                    "error_code": "WINDOW_BUNDLE_MISMATCH",
                    "error": f"window {window_id} does not match bundle: {target_bundle}",
                    "window": None,
                    "windows": windows,
                }
            return {"success": True, "window": matched_window, "windows": windows}

        if target_bundle:
            visible_matches = [
                w for w in windows
                if w.get("is_visible") and normalize_bundle_name(w.get("bundle_name")) == target_bundle
            ]
            matched_window = visible_matches[0] if visible_matches else None
            if not matched_window:
                any_matches = [w for w in windows if normalize_bundle_name(w.get("bundle_name")) == target_bundle]
                matched_window = any_matches[0] if any_matches else None
            if not matched_window:
                return {
                    "success": False,
                    "error_code": "WINDOW_NOT_FOUND",
                    "error": f"window not found for bundle: {target_bundle}",
                    "window": None,
                    "windows": windows,
                }
            return {"success": True, "window": matched_window, "windows": windows}

        for window in windows:
            if window.get("is_visible"):
                return {"success": True, "window": window, "windows": windows}
        return {"success": True, "window": windows[0], "windows": windows}
