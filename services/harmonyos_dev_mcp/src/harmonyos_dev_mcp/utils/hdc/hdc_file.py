"""File and hilog helpers for hdc-backed device operations."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger


class HdcFile:
    """File transfer and hilog-related helpers."""

    def push_file(self, device_id: str, local_path: str, remote_path: str) -> bool:
        """Push a local file to the device."""
        logger.info(f"push file: {local_path} -> {remote_path}")
        result = self._execute_command(
            [
                "-t",
                device_id,
                "file",
                "send",
                local_path,
                remote_path,
            ]
        )

        if result["success"]:
            logger.info("push file succeeded")
            return True

        logger.error(f"push file failed: {result['stderr']}")
        return False

    def pull_file(self, device_id: str, remote_path: str, local_path: str) -> bool:
        """Pull a file from the device."""
        logger.info(f"pull file: {remote_path} -> {local_path}")
        result = self._execute_command(
            [
                "-t",
                device_id,
                "file",
                "recv",
                remote_path,
                local_path,
            ]
        )

        if result["success"]:
            logger.info("pull file succeeded")
            return True

        logger.error(f"pull file failed: {result['stderr']}")
        return False

    def list_hilog_files(self, device_id: str, hilog_dir: str = "/data/log/hilog") -> Dict[str, Any]:
        """List hilog files under the target directory."""
        logger.info(f"list hilog files on device {device_id}: {hilog_dir}")

        result = self.execute_shell(device_id, f"ls -la {hilog_dir}")
        if not result["success"]:
            return {
                "success": False,
                "error": result.get("stderr", "cannot access hilog directory"),
                "files": [],
                "raw_output": result.get("stdout", ""),
            }

        files: List[Dict[str, Any]] = []
        raw_lines: List[str] = []

        for line in result["stdout"].split("\n"):
            line = line.strip()
            if not line or line.startswith("total"):
                continue

            raw_lines.append(line)
            if line.startswith("d"):
                continue

            parts = line.split()
            if len(parts) < 6:
                continue

            filename = parts[-1]
            if not (filename.startswith("hilog") or "hilog" in filename):
                continue

            try:
                size = 0
                for part in parts[1:-1]:
                    if part.isdigit() and int(part) > 100:
                        size = int(part)
                        break

                timestamp = None
                name_without_gz = filename.removesuffix(".gz")
                if "-" in name_without_gz:
                    time_part = name_without_gz.split(".")[-1]
                    if len(time_part) >= 15 and time_part[0].isdigit():
                        try:
                            timestamp = datetime.strptime(time_part, "%Y%m%d-%H%M%S")
                        except ValueError:
                            try:
                                date_part = time_part.split("-")[0]
                                if len(date_part) == 8:
                                    timestamp = datetime.strptime(date_part, "%Y%m%d")
                            except ValueError:
                                pass

                files.append(
                    {
                        "name": filename,
                        "path": f"{hilog_dir}/{filename}",
                        "size": size,
                        "timestamp": timestamp.isoformat() if timestamp else None,
                        "timestamp_dt": timestamp,
                    }
                )
                logger.debug(f"found hilog file: {filename}, timestamp={timestamp}")
            except (ValueError, IndexError) as exc:
                logger.warning(f"failed to parse hilog file info: {line}, error: {exc}")

        files.sort(key=lambda item: item.get("timestamp") or "", reverse=True)
        return {
            "success": True,
            "files": files,
            "count": len(files),
            "directory": hilog_dir,
            "raw_line_count": len(raw_lines),
        }

    def pull_hilog_files(
        self,
        device_id: str,
        files: List[Dict[str, Any]],
        local_dir: str,
    ) -> Dict[str, Any]:
        """Pull selected hilog files to a local directory."""
        os.makedirs(local_dir, exist_ok=True)

        pulled_files: List[Dict[str, Any]] = []
        failed_files: List[str] = []

        for file_info in files:
            remote_path = file_info["path"]
            local_path = os.path.join(local_dir, file_info["name"])

            logger.info(f"pull hilog file: {remote_path} -> {local_path}")
            if self.pull_file(device_id, remote_path, local_path):
                pulled_files.append(
                    {
                        "name": file_info["name"],
                        "local_path": local_path,
                        "size": file_info["size"],
                        "timestamp": file_info.get("timestamp"),
                    }
                )
            else:
                failed_files.append(file_info["name"])

        return {
            "success": len(pulled_files) > 0,
            "pulled_files": pulled_files,
            "failed_files": failed_files,
            "local_dir": local_dir,
        }

    def get_realtime_logs(
        self,
        device_id: str,
        lines: int = 100,
        tag: Optional[str] = None,
        bundle_name: Optional[str] = None,
        pid: Optional[int] = None,
    ) -> str:
        """Return a full `hilog -x` snapshot for downstream filtering."""
        logger.info(f"get realtime logs for device {device_id}")

        cmd = ["-t", device_id, "shell"]
        hilog_cmd = "hilog -x"

        if tag:
            hilog_cmd += f" -T {tag}"

        if pid:
            hilog_cmd += f" -P {pid}"

        if bundle_name:
            hilog_cmd += f' | grep "{bundle_name}"'

        cmd.append(hilog_cmd)
        result = self._execute_command(cmd, timeout=10)

        if result["success"]:
            log_lines = [line for line in result["stdout"].split("\n") if line.strip()]
            return "\n".join(log_lines)

        logger.error(f"get realtime logs failed: {result['stderr']}")
        return ""
