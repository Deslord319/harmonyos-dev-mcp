"""Build/deploy tools for HarmonyOS."""

import asyncio
import os
import re
import time
from typing import Any, Dict, List, Optional

from loguru import logger

from common.tools.registry import mcp_tool

from ..container import get_hdc
from ..types import BuildResult, InstallResult, RunAppResult, UninstallResult
from ..utils.wrappers.hvigor_wrapper import HvigorWrapper
from .device_support import DeviceToolSupport
from common.tools.response import error_result, from_action_result, mcp_response, ok_result

MAX_ERRORS = 15
BUILD_TIMEOUT_HINT = "Set MCP tools/call timeout to at least 60 seconds; 120 seconds is recommended for cold builds."
ALLOWED_BUILD_MODES = {"debug", "release"}


@mcp_tool(category="build")
@mcp_response("build_app")
@DeviceToolSupport.handle_tool_error("BUILD_ERROR", output_path=None, target="hap", duration=0)
async def build_app(
    project_path: str,
    build_mode: str = "debug",
    target: str = "hap",
    product: str = "default",
    module_name: Optional[str] = None,
) -> BuildResult:
    """Build HarmonyOS artifact."""
    if not project_path or not os.path.isdir(project_path):
        return error_result(
            "INVALID_PROJECT_PATH",
            "project_path must be an existing directory",
            result={"output_path": None, "target": target, "duration": 0, "errors": [], "error_count": 0},
        )
    if build_mode not in ALLOWED_BUILD_MODES:
        return error_result(
            "INVALID_BUILD_MODE",
            'build_mode must be one of "debug" or "release"',
            result={"output_path": None, "target": target, "duration": 0, "errors": [], "error_count": 0},
        )
    if target not in {"hap", "har", "app"}:
        return error_result(
            "INVALID_BUILD_TARGET",
            'target must be one of "hap", "har", or "app"',
            result={"output_path": None, "target": target, "duration": 0, "errors": [], "error_count": 0},
        )
    if target == "har" and not module_name:
        return error_result(
            "MISSING_MODULE_NAME",
            'module_name is required when target="har"',
            result={"output_path": None, "target": target, "duration": 0, "errors": [], "error_count": 0},
        )

    start_time = time.time()
    logger.warning(
        f"build_app is a long-running task; ensure MCP client timeout is >= 60s, "
        f"preferably 120s for cold builds (project={project_path}, mode={build_mode}, target={target})"
    )
    hvigor = HvigorWrapper(project_path)
    raw = await asyncio.to_thread(
        hvigor.build,
        target=target,
        build_mode=build_mode,
        product=product,
        module_name=module_name,
    )
    elapsed = round(time.time() - start_time, 2)

    payload: dict = {
        "output_path": raw.get("output_path"),
        "target": target,
        "duration": elapsed,
        "errors": [],
        "error_count": 0,
    }

    if raw.get("success", False):
        return ok_result(payload)

    errors = _extract_build_errors(raw)
    payload["errors"] = errors[:MAX_ERRORS]
    payload["error_count"] = len(errors)
    detail = _extract_detailed_error_output(raw) or "build failed"
    if raw.get("error_code") == "BUILD_TIMEOUT":
        detail = f"{detail}. {BUILD_TIMEOUT_HINT}"
    return error_result(raw.get("error_code", "BUILD_FAILED"), detail, result=payload)


def _extract_build_errors(build_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    all_errors: List[Dict[str, Any]] = []
    seen = set()
    for source in ("stdout", "stderr"):
        text = build_result.get(source, "")
        if not text:
            continue
        for err in _parse_errors_from_text(text, source):
            key = (err.get("file", ""), err.get("line", 0), err.get("message", "")[:50])
            if key in seen:
                continue
            seen.add(key)
            all_errors.append(err)
    return all_errors


def _parse_errors_from_text(text: str, source: str) -> List[Dict[str, Any]]:
    errors: List[Dict[str, Any]] = []
    cleaned = re.sub(r"\x1b\[[0-9;]*m", "", text)
    cleaned = re.sub(r"\n\s*At File:", " At File:", cleaned)

    patterns = [
        re.compile(r"Error Message:\s*(.+?)\s*At File:\s*(.+?\.(?:ts|ets|js)):?(\d+):?(\d+)", re.IGNORECASE),
        re.compile(r"^(.+?\.(?:ts|ets|js))\((\d+),(\d+)\):\s*(?:error|ERROR)\s*(?:\w+)?\s*:\s*(.+)$"),
        re.compile(r"^(?:ERROR|Error)\s*[:：]?\s*(.+?\.(?:ts|ets|js|json5?)):(\d+)(?::(\d+))?\s*[-:]?\s*(.+)$"),
        re.compile(r"^(.+?\.(?:ts|ets|js|json5?)):(\d+):(\d+)\s*[-:]?\s*(?:error|ERROR)\s*(.+)$"),
        re.compile(r"^(?:ERROR|Error)\s+File:\s*(.+?\.(?:ts|ets|js|json5?))\s+line:\s*(\d+)\s+column:\s*(\d+)\s*[-:]?\s*(.+)$"),
    ]

    for line in cleaned.splitlines():
        line = line.strip()
        if not line:
            continue
        for pattern in patterns:
            match = pattern.search(line)
            if not match:
                continue
            groups = match.groups()
            if len(groups) != 4:
                continue
            file_path, line_num, col, message = groups
            errors.append(
                {
                    "file": _normalize_path(file_path.strip()),
                    "line": int(line_num) if str(line_num).isdigit() else 0,
                    "column": int(col) if str(col).isdigit() else 0,
                    "message": (message or "").strip(),
                    "type": _classify_error((message or "").strip()),
                    "source": source,
                }
            )
            break

    return errors


def _extract_detailed_error_output(build_result: Dict[str, Any]) -> str:
    stderr = (build_result.get("stderr") or "").strip()
    stdout = (build_result.get("stdout") or "").strip()
    if stderr and stdout:
        return f"{stderr}\n{stdout}"
    return stderr or stdout


def _normalize_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    is_absolute = normalized.startswith("/") or ":" in normalized[:3]
    if not is_absolute:
        return path

    prefixes = ["/entry/", "/build/", "/src/", "\\entry\\", "\\build\\", "\\src\\"]
    for prefix in prefixes:
        if prefix in path or prefix.replace("/", "\\") in path:
            idx = max(path.find(prefix), path.find(prefix.replace("/", "\\")))
            if idx >= 0:
                return path[idx + 1 :]
    parts = normalized.split("/")
    for i, part in enumerate(parts):
        if part in ["src", "entry", "build"]:
            return "/".join(parts[i:])
    return parts[-1] if parts else path


def _classify_error(message: str) -> str:
    message_lower = message.lower()
    if any(kw in message_lower for kw in ["cannot find", "not found", "no such", "does not exist"]):
        return "missing"
    if any(kw in message_lower for kw in ["type", "cannot be assigned", "is not compatible"]):
        return "type"
    if any(kw in message_lower for kw in ["syntax", "unexpected", "expected"]):
        return "syntax"
    if any(kw in message_lower for kw in ["import", "export", "module"]):
        return "module"
    if any(kw in message_lower for kw in ["permission", "denied", "access"]):
        return "permission"
    if any(kw in message_lower for kw in ["config", "profile", "json", "schema"]):
        return "config"
    return "compile"


@mcp_tool(category="build")
@mcp_response("install_app")
@DeviceToolSupport.handle_tool_error("INSTALL_ERROR", hap_path="")
@DeviceToolSupport.with_device(hap_path="")
async def install_app(hap_path: str, device_id: Optional[str] = None) -> InstallResult:
    if not hap_path:
        return error_result(
            "MISSING_HAP_PATH",
            "hap_path is required",
            result={"device_id": device_id, "hap_path": ""},
        )
    if not hap_path.lower().endswith((".hap", ".app")):
        return error_result(
            "INVALID_APP_PACKAGE",
            "hap_path must point to a .hap or .app package",
            result={"device_id": device_id, "hap_path": hap_path},
        )
    hdc = get_hdc()
    raw = await asyncio.to_thread(hdc.install_app, device_id, hap_path)
    if isinstance(raw, bool):
        raw = {"success": raw}
    return from_action_result(
        raw,
        default_code="INSTALL_FAILED",
        default_detail="install app failed",
        default_result={"device_id": device_id, "hap_path": hap_path},
    )


@mcp_tool(category="build")
@mcp_response("run_app")
@DeviceToolSupport.handle_tool_error(
    "RUN_APP_ERROR",
    bundle_name="",
    ability_name="",
    module_name="entry",
    auto_detected=False,
    command_success=False,
    window_found=False,
    window=None,
)
@DeviceToolSupport.with_device(
    bundle_name="",
    ability_name="",
    module_name="entry",
    auto_detected=False,
    command_success=False,
    window_found=False,
    window=None,
)
async def run_app(
    bundle_name: str,
    device_id: Optional[str] = None,
    ability_name: Optional[str] = None,
    module_name: Optional[str] = None,
    auto_detect: bool = True,
) -> RunAppResult:
    hdc = get_hdc()

    final_ability, final_module, auto_detected = await asyncio.to_thread(
        _resolve_ability,
        hdc,
        device_id,
        bundle_name,
        ability_name,
        module_name,
        auto_detect,
    )

    if not final_ability:
        return error_result(
            "ABILITY_RESOLUTION_FAILED",
            "failed to resolve launch ability automatically; provide ability_name explicitly",
            result={
                "device_id": device_id,
                "bundle_name": bundle_name,
                "ability_name": "",
                "module_name": final_module or module_name or "entry",
                "auto_detected": auto_detected,
                "command_success": False,
                "window_found": False,
                "window": None,
            },
        )

    start_result = await asyncio.to_thread(hdc.start_app, device_id, bundle_name, final_ability, final_module)

    payload = {
        "device_id": device_id,
        "bundle_name": bundle_name,
        "ability_name": final_ability or "",
        "module_name": final_module or "entry",
        "auto_detected": auto_detected,
        "command_success": start_result.get("command_success", False),
        "window_found": start_result.get("window_found", False),
        "window": start_result.get("window"),
    }
    if start_result.get("command_success") and start_result.get("window_found") is False:
        start_result = dict(start_result)
        start_result["error"] = "app launch command succeeded, but window verification did not pass"
    return from_action_result(
        start_result,
        default_code="RUN_APP_FAILED",
        default_detail="run app failed",
        default_result=payload,
    )


def _resolve_ability(
    hdc,
    device_id: str,
    bundle_name: str,
    ability_name: str,
    module_name: str,
    auto_detect: bool,
):
    final_ability = ability_name
    final_module = module_name
    auto_detected = False

    if not final_ability and auto_detect:
        result = hdc.get_main_ability(device_id, bundle_name)
        candidates = result.get("candidates", []) if isinstance(result, dict) else []
        idx = result.get("recommended", -1) if isinstance(result, dict) else -1

        if result.get("success", False) and candidates and 0 <= idx < len(candidates):
            chosen = candidates[idx]
            final_ability = chosen.get("ability_name", "")
            final_module = final_module or chosen.get("module_name")
            auto_detected = True
            logger.debug(f"auto detected main ability: {final_ability}, module: {final_module}")
        else:
            pkg_info = hdc.get_package_info(device_id, bundle_name)
            if pkg_info.get("success"):
                abilities = pkg_info.get("abilities", [])
                for ability in abilities:
                    if ability.get("type") == "page" and ability.get("visible", True):
                        final_ability = ability.get("name")
                        final_module = final_module or ability.get("module", "entry")
                        auto_detected = True
                        break
                if not final_ability:
                    for ability in abilities:
                        if ability.get("type") == "page":
                            final_ability = ability.get("name")
                            final_module = final_module or ability.get("module", "entry")
                            auto_detected = True
                            break

    return (final_ability, final_module or "entry", auto_detected)


@mcp_tool(category="build")
@mcp_response("uninstall_app")
@DeviceToolSupport.handle_tool_error("UNINSTALL_ERROR", bundle_name="")
@DeviceToolSupport.with_device(bundle_name="")
async def uninstall_app(bundle_name: str, device_id: Optional[str] = None) -> UninstallResult:
    if not bundle_name:
        return error_result(
            "MISSING_BUNDLE_NAME",
            "bundle_name is required",
            result={"device_id": device_id, "bundle_name": ""},
        )
    hdc = get_hdc()
    raw = await asyncio.to_thread(hdc.uninstall_app, device_id, bundle_name)
    if isinstance(raw, bool):
        raw = {"success": raw}
    return from_action_result(
        raw,
        default_code="UNINSTALL_FAILED",
        default_detail="uninstall app failed",
        default_result={"device_id": device_id, "bundle_name": bundle_name},
    )
