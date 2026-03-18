"""General HarmonyOS MCP tools."""

import asyncio
from typing import Literal, Optional

from common.tools.registry import mcp_tool

from ..container import get_hdc
from ..types import ListDevicesResult, QueryPackageResult
from .device_base import ToolBase
from common.tools.response import error_result, from_action_result, mcp_response, ok_result

_LIST_ERROR_DEFAULTS = {"packages": [], "count": 0}
_ABILITIES_ERROR_DEFAULTS = {"abilities": [], "modules": [], "main_ability": None, "ability_count": 0}
_MAIN_ABILITY_ERROR_DEFAULTS = {"ability_name": "", "module_name": ""}
_PERMISSIONS_ERROR_DEFAULTS = {"requested_permissions": [], "permission_count": 0}


@mcp_tool(category="general")
@mcp_response("list_devices")
@ToolBase.handle_tool_error("DEVICE_LIST_ERROR", devices=[], count=0)
async def list_devices() -> ListDevicesResult:
    hdc = get_hdc()
    devices = await asyncio.to_thread(hdc.list_devices_with_info)
    return ok_result({"devices": devices, "count": len(devices)})


@mcp_tool(category="general")
@mcp_response("query_package")
@ToolBase.handle_tool_error("QUERY_PACKAGE_ERROR", info_type="list", **_LIST_ERROR_DEFAULTS)
@ToolBase.with_device(info_type="list", **_LIST_ERROR_DEFAULTS)
async def query_package(
    device_id: Optional[str] = None,
    bundle_name: Optional[str] = None,
    keyword: Optional[str] = None,
    info_type: Literal["list", "abilities", "main_ability", "permissions"] = "list",
) -> QueryPackageResult:
    hdc = get_hdc()

    if info_type in ("abilities", "main_ability", "permissions") and not bundle_name:
        return error_result(
            "MISSING_BUNDLE_NAME",
            f'info_type="{info_type}" requires bundle_name',
            result={"device_id": device_id, "info_type": info_type},
        )

    if bundle_name and info_type == "list":
        info_type = "abilities"

    if info_type == "list":
        raw = await asyncio.to_thread(hdc.list_packages, device_id, keyword)
        return from_action_result(
            raw,
            default_code="LIST_PACKAGES_ERROR",
            default_detail="failed to list packages",
            default_result={
                "device_id": device_id,
                "info_type": "list",
                "packages": raw.get("packages", []) if isinstance(raw, dict) else [],
                "count": raw.get("count", len(raw.get("packages", []))) if isinstance(raw, dict) else 0,
                "keyword": keyword or "",
            },
        )

    if info_type == "abilities":
        raw = await asyncio.to_thread(hdc.get_package_info, device_id, bundle_name)
        if not raw.get("success", False):
            return error_result(
                raw.get("error_code", "GET_ABILITIES_ERROR"),
                raw.get("error", "failed to get abilities"),
                result={
                    "device_id": device_id,
                    "info_type": "abilities",
                    "bundle_name": bundle_name,
                    **_ABILITIES_ERROR_DEFAULTS,
                },
            )

        raw_abilities = raw.get("abilities", [])
        abilities = [
            {"name": a.get("name", ""), "module": a.get("module", ""), "type": a.get("type", "")}
            for a in raw_abilities
        ]
        raw_modules = raw.get("modules", [])
        modules = [m.get("name", m) if isinstance(m, dict) else m for m in raw_modules]
        raw_main = raw.get("main_ability")
        main_ability = None
        if raw_main:
            main_ability = {
                "name": raw_main.get("name", ""),
                "module": raw_main.get("module", ""),
                "type": raw_main.get("type", ""),
            }

        return ok_result(
            {
                "device_id": device_id,
                "info_type": "abilities",
                "bundle_name": bundle_name,
                "abilities": abilities,
                "modules": modules,
                "main_ability": main_ability,
                "ability_count": len(abilities),
            }
        )

    if info_type == "main_ability":
        raw = await asyncio.to_thread(hdc.get_main_ability, device_id, bundle_name)
        if not raw.get("success", False):
            return error_result(
                raw.get("error_code", "GET_MAIN_ABILITY_ERROR"),
                raw.get("error", "failed to get main ability"),
                result={
                    "device_id": device_id,
                    "info_type": "main_ability",
                    "bundle_name": bundle_name,
                    **_MAIN_ABILITY_ERROR_DEFAULTS,
                },
            )

        candidates = raw.get("candidates", [])
        idx = raw.get("recommended", -1)
        ability_name = ""
        module_name = ""
        if isinstance(candidates, list) and 0 <= idx < len(candidates):
            picked = candidates[idx]
            ability_name = picked.get("ability_name", "")
            module_name = picked.get("module_name", "")

        return ok_result(
            {
                "device_id": device_id,
                "info_type": "main_ability",
                "bundle_name": bundle_name,
                "ability_name": ability_name,
                "module_name": module_name,
                "candidates": candidates,
                "recommended": idx,
            }
        )

    if info_type == "permissions":
        raw = await asyncio.to_thread(hdc.get_package_permissions, device_id, bundle_name)
        return from_action_result(
            raw,
            default_code="GET_PERMISSIONS_ERROR",
            default_detail="failed to get permissions",
            default_result={
                "device_id": device_id,
                "info_type": "permissions",
                "bundle_name": bundle_name,
                "requested_permissions": raw.get("requested_permissions", []) if isinstance(raw, dict) else [],
                "permission_count": raw.get("permission_count", 0) if isinstance(raw, dict) else 0,
            },
        )

    return error_result(
        "INVALID_INFO_TYPE",
        f"unsupported info_type: {info_type}",
        result={"device_id": device_id, "info_type": info_type},
    )
