"""Device and log tool tests with standardized MCP response envelope."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from harmonyos_dev_mcp.config import LogSecurityConfig


class TestListDevices:
    @pytest.mark.asyncio
    async def test_returns_device_list(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import general

        sc = unwrap_result(await general.list_devices())

        assert sc["ok"] is True
        assert sc["result"]["count"] == len(sc["result"]["devices"])
        assert isinstance(sc["result"]["devices"], list)
        if sc["result"]["devices"]:
            assert "device_id" in sc["result"]["devices"][0]

    @pytest.mark.asyncio
    async def test_handles_empty_devices(self, no_device_mock: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import general

        sc = unwrap_result(await general.list_devices())

        assert sc["ok"] is True
        assert sc["result"]["count"] == 0
        assert sc["result"]["devices"] == []

    @pytest.mark.asyncio
    async def test_handles_exception(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import general

        mock_hdc.list_devices_with_info.side_effect = Exception("Connection failed")

        sc = unwrap_result(await general.list_devices())

        assert sc["ok"] is False
        assert "Connection failed" in sc["error"]["detail"]


class TestQueryPackage:
    @pytest.mark.asyncio
    async def test_invalid_info_type_returns_supported_values(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import general

        sc = unwrap_result(await general.query_package(bundle_name="com.example.app", info_type="basic"))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "INVALID_INFO_TYPE"
        assert "list, abilities, main_ability, permissions" in sc["error"]["detail"]
        assert '"basic" is not supported' in sc["error"]["detail"]

    @pytest.mark.asyncio
    async def test_main_ability_uses_recommended_candidate_fields(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import general

        mock_hdc.get_main_ability.return_value = {
            "success": True,
            "candidates": [{"ability_name": "EntryAbility", "module_name": "entry"}],
            "recommended": 0,
        }

        sc = unwrap_result(await general.query_package(bundle_name="com.example.app", info_type="main_ability"))

        assert sc["ok"] is True
        assert sc["result"]["ability_name"] == "EntryAbility"
        assert sc["result"]["module_name"] == "entry"

    @pytest.mark.asyncio
    async def test_permissions_query_returns_permissions_payload(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import general

        mock_hdc.get_package_permissions.return_value = {
            "success": True,
            "requested_permissions": ["ohos.permission.INTERNET"],
            "permission_count": 1,
        }

        sc = unwrap_result(await general.query_package(bundle_name="com.example.app", info_type="permissions"))

        assert sc["ok"] is True
        assert sc["result"]["requested_permissions"] == ["ohos.permission.INTERNET"]
        assert sc["result"]["permission_count"] == 1

    @pytest.mark.asyncio
    async def test_bundle_name_with_list_request_echoes_requested_type(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import general

        sc = unwrap_result(await general.query_package(bundle_name="com.example.app", info_type="list"))

        assert sc["ok"] is True
        assert sc["result"]["requested_info_type"] == "list"
        assert sc["result"]["info_type"] == "abilities"


class TestUiTree:
    @pytest.mark.asyncio
    async def test_list_windows_maps_rect_to_bounds(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import e2e

        sc = unwrap_result(await e2e.list_windows())

        assert sc["ok"] is True
        window = sc["result"]["windows"][0]
        assert window["bounds"] == {"left": 10, "top": 20, "right": 310, "bottom": 420}
        assert window["bundle_name_resolved"] is True

    @pytest.mark.asyncio
    async def test_list_windows_filters_by_bundle_name(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import e2e

        mock_hdc.get_window_list.return_value = {
            "success": True,
            "count": 2,
            "windows": [
                {
                    "window_id": 1,
                    "window_name": "settings0",
                    "bundle_name": "com.huawei.hmos.settings",
                    "is_visible": True,
                    "rect": {"x": 10, "y": 20, "w": 300, "h": 400},
                },
                {
                    "window_id": 2,
                    "window_name": "securitytool0",
                    "bundle_name": "com.huawei.securitytool",
                    "is_visible": True,
                    "rect": {"x": 30, "y": 40, "w": 500, "h": 600},
                },
            ],
        }

        sc = unwrap_result(await e2e.list_windows(bundle_name="com.huawei.hmos.settings"))

        assert sc["ok"] is True
        assert sc["result"]["count"] == 1
        assert sc["result"]["total_count"] == 2
        assert sc["result"]["windows"][0]["bundle_name"] == "com.huawei.hmos.settings"

    @pytest.mark.asyncio
    async def test_list_windows_bundle_filter_can_return_empty(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import e2e

        sc = unwrap_result(await e2e.list_windows(bundle_name="com.example.missing"))

        assert sc["ok"] is True
        assert sc["result"]["count"] == 0
        assert sc["result"]["windows"] == []

    @pytest.mark.asyncio
    async def test_list_windows_marks_unresolved_bundle_name(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import e2e

        mock_hdc.get_window_list.return_value = {
            "success": True,
            "count": 1,
            "windows": [
                {
                    "window_id": 7,
                    "window_name": "FloatingPanel",
                    "bundle_name": None,
                    "is_visible": False,
                    "rect": {"x": 1, "y": 2, "w": 3, "h": 4},
                }
            ],
        }

        sc = unwrap_result(await e2e.list_windows())

        assert sc["ok"] is True
        window = sc["result"]["windows"][0]
        assert window["bundle_name"] == ""
        assert window["bundle_name_resolved"] is False
        assert window["bounds"] == {"left": 1, "top": 2, "right": 4, "bottom": 6}

    @pytest.mark.asyncio
    async def test_list_windows_returns_parse_error(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import e2e

        mock_hdc.get_window_list.return_value = {
            "success": False,
            "error_code": "LIST_WINDOWS_PARSE_ERROR",
            "error": "failed to parse window list header",
            "windows": [],
        }

        sc = unwrap_result(await e2e.list_windows())

        assert sc["ok"] is False
        assert sc["error"]["code"] == "LIST_WINDOWS_PARSE_ERROR"

    @pytest.mark.asyncio
    async def test_get_ui_tree_returns_list_windows_error_when_window_query_fails_for_targeted_lookup(
        self, mock_hdc: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import e2e

        mock_hdc.get_window_list.return_value = {"success": False, "error": "wm failed", "error_code": "LIST_WINDOWS_ERROR"}

        sc = unwrap_result(await e2e.get_ui_tree(bundle_name="com.example.app"))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "LIST_WINDOWS_ERROR"
        assert sc["error"]["detail"] == "wm failed"

    @pytest.mark.asyncio
    async def test_get_ui_tree_returns_no_windows_when_targeted_lookup_window_list_empty(
        self, mock_hdc: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import e2e

        mock_hdc.get_window_list.return_value = {"success": True, "windows": [], "count": 0}

        sc = unwrap_result(await e2e.get_ui_tree(bundle_name="com.example.app"))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "NO_WINDOWS"

    @pytest.mark.asyncio
    async def test_get_ui_tree_without_target_does_not_query_windows(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import e2e

        sc = unwrap_result(await e2e.get_ui_tree())

        assert sc["ok"] is True
        assert sc["result"]["validation_applied"] is False
        assert sc["result"]["validated_window_id"] is None
        assert sc["result"]["capture_scope"] == "global_dump"
        mock_hdc.get_window_list.assert_not_called()
        mock_hdc.get_ui_tree_raw.assert_called_once_with("device_001", None)

    @pytest.mark.asyncio
    async def test_get_ui_tree_with_bundle_name_validates_target_window(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import e2e

        sc = unwrap_result(await e2e.get_ui_tree(bundle_name="com.example.app"))

        assert sc["ok"] is True
        assert sc["result"]["validation_applied"] is True
        assert sc["result"]["validated_window_id"] == 1
        assert sc["result"]["capture_scope"] == "validated_global_dump"
        mock_hdc.resolve_window_target.assert_called_once_with("device_001", bundle_name="com.example.app", window_id=None)
        mock_hdc.get_ui_tree_raw.assert_called_once_with("device_001", 1)

    @pytest.mark.asyncio
    async def test_get_ui_tree_rejects_bundle_when_not_explicitly_resolved(
        self, mock_hdc: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import e2e

        mock_hdc.get_window_list.return_value = {
            "success": True,
            "count": 1,
            "windows": [
                {
                    "window_id": 1,
                    "window_name": "app0",
                    "bundle_name": "",
                    "is_visible": True,
                    "rect": {"x": 10, "y": 20, "w": 300, "h": 400},
                }
            ],
        }

        sc = unwrap_result(await e2e.get_ui_tree(bundle_name="com.example.app"))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "WINDOW_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_ui_tree_with_window_id_validates_window_exists(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import e2e

        sc = unwrap_result(await e2e.get_ui_tree(window_id=1))

        assert sc["ok"] is True
        assert sc["result"]["validated_window_id"] == 1
        mock_hdc.resolve_window_target.assert_called_once_with("device_001", bundle_name=None, window_id=1)
        mock_hdc.get_ui_tree_raw.assert_called_once_with("device_001", 1)

    @pytest.mark.asyncio
    async def test_get_ui_tree_rejects_unknown_window_id(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import e2e

        sc = unwrap_result(await e2e.get_ui_tree(window_id=999))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "WINDOW_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_ui_tree_rejects_window_bundle_mismatch(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import e2e

        mock_hdc.get_window_list.return_value = {
            "success": True,
            "count": 1,
            "windows": [
                {
                    "window_id": 7,
                    "window_name": "settings0",
                    "bundle_name": "com.example.settings",
                    "is_visible": True,
                    "rect": {"x": 1, "y": 2, "w": 3, "h": 4},
                }
            ],
        }

        sc = unwrap_result(await e2e.get_ui_tree(bundle_name="com.example.app", window_id=7))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "WINDOW_BUNDLE_MISMATCH"

    @pytest.mark.asyncio
    async def test_get_ui_tree_rejects_invalid_payload_shape(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import e2e

        mock_hdc.get_ui_tree_raw.return_value = {"success": True, "ui_tree": 123}

        sc = unwrap_result(await e2e.get_ui_tree())

        assert sc["ok"] is False
        assert sc["error"]["code"] == "INVALID_UI_TREE_PAYLOAD"


class TestLogsQuery:
    def test_saved_log_cleanup_removes_expired_snapshots(self, monkeypatch, tmp_path):
        from harmonyos_dev_mcp.tools.log import query

        hm_dir = tmp_path / "hm_logs"
        hm_dir.mkdir()
        expired = hm_dir / "hilog_snapshot_old.txt"
        recent = hm_dir / "hilog_snapshot_new.txt"
        expired.write_text("old", encoding="utf-8")
        recent.write_text("new", encoding="utf-8")

        old_time = (datetime.now() - timedelta(days=LogSecurityConfig.AUTO_CLEANUP_DAYS + 1)).timestamp()
        recent_time = datetime.now().timestamp()

        import os

        os.utime(expired, (old_time, old_time))
        os.utime(recent, (recent_time, recent_time))

        monkeypatch.setattr(query, "HM_LOG_DIR", hm_dir)

        result = query._cleanup_old_saved_logs()

        assert result["cleaned"] == 1
        assert not expired.exists()
        assert recent.exists()

    @pytest.mark.asyncio
    async def test_direct_logs_input(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools.log import logs_query

        test_logs = [
            "01-31 10:00:00.123  1000  2000 E MyApp: test error",
            "01-31 10:00:01.456  1000  2000 I MyApp: test info",
        ]
        sc = unwrap_result(await logs_query(logs=test_logs))

        assert sc["ok"] is True
        assert sc["result"]["query_mode"] == "errors"
        assert sc["result"]["source_used"] == "direct"
        assert sc["result"]["matched"] is True
        assert len(sc["result"]["items"]) == 1
        assert sc["result"]["items"][0]["type"] == "error"

    @pytest.mark.asyncio
    async def test_level_filter(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools.log import logs_query

        test_logs = [
            "01-31 10:00:00.123  1000  2000 E MyApp: error",
            "01-31 10:00:01.456  1000  2000 I MyApp: info",
            "01-31 10:00:02.789  1000  2000 W MyApp: warning",
        ]
        sc = unwrap_result(await logs_query(logs=test_logs, level="E"))

        assert sc["ok"] is True
        assert len(sc["result"]["items"]) == 1

    @pytest.mark.asyncio
    async def test_seconds_accepts_numeric_string(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools.log import logs_query

        test_logs = [
            "01-31 10:00:00.123  1000  2000 E MyApp: error",
            "01-31 10:00:01.456  1000  2000 I MyApp: info",
        ]
        sc = unwrap_result(await logs_query(logs=test_logs, seconds="30"))

        assert sc["ok"] is True
        assert sc["result"]["filters_applied"]["seconds"] == 30

    @pytest.mark.asyncio
    async def test_markers_mode_finds_success_markers(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools.log import logs_query

        test_logs = [
            "2026-03-19 10:00:00.123  40683  40683 I A03D00/com.huawei.securitytool/JSAPP: [picker] getDocumentPickerSaveResult saveResult: errorcode is = 0, selecturi is = file://docs/storage/Users/currentUser/Download/demo.txt",
            "2026-03-19 10:00:00.456  40683  40683 I picker: resCode is 0",
        ]

        sc = unwrap_result(
            await logs_query(
                logs=test_logs,
                mode="markers",
                package_name="com.huawei.securitytool",
                context_lines=1,
            )
        )

        assert sc["ok"] is True
        assert sc["result"]["query_mode"] == "markers"
        assert sc["result"]["matched"] is True
        assert sc["result"]["match_count"] == 2
        assert sc["result"]["group_count"] == 2
        assert sc["result"]["items"][0]["type"] == "marker_success"
        assert "saveResult" in sc["result"]["items"][0]["matched_keywords"]
        assert sc["result"]["items"][0]["match_strength"] == "strong"
        assert sc["result"]["items"][0]["score"] > 0

    @pytest.mark.asyncio
    async def test_errors_mode_does_not_flag_success_errorcode_zero(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools.log import logs_query

        test_logs = [
            "2026-03-19 10:00:00.123  40683  40683 I A03D00/com.huawei.securitytool/JSAPP: [picker] getDocumentPickerSaveResult saveResult: errorcode is = 0",
            "2026-03-19 10:00:01.123  40683  40683 E MyApp: actual failure happened",
        ]

        sc = unwrap_result(await logs_query(logs=test_logs))

        assert sc["ok"] is True
        assert sc["result"]["matched"] is True
        assert sc["result"]["match_count"] == 1
        assert sc["result"]["group_count"] == 1
        assert sc["result"]["items"][0]["message"] == "actual failure happened"

    @pytest.mark.asyncio
    async def test_invalid_mode_returns_clear_error(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools.log import logs_query

        sc = unwrap_result(await logs_query(logs=["01-31 10:00:00.123  1  1 I Tag: ok"], mode="raw"))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "INVALID_QUERY_MODE"
        assert "errors, markers" in sc["error"]["detail"]

    @pytest.mark.asyncio
    async def test_fails_when_no_device(self, no_device_mock: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools.log import logs_query

        sc = unwrap_result(await logs_query())

        assert sc["ok"] is False
        assert sc["error"]["detail"]

    @pytest.mark.asyncio
    async def test_package_name_no_longer_requires_running_app(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools.log import logs_query

        mock_hdc.get_app_pid.return_value = None
        mock_hdc.get_realtime_logs.return_value = (
            "2026-03-19 10:00:00.123  9999  9999 I picker: export completed\n"
            "2026-03-19 10:00:00.456  9999  9999 I A03D00/com.huawei.securitytool/JSAPP: saveResult success"
        )

        sc = unwrap_result(
            await logs_query(package_name="com.huawei.securitytool", mode="markers", realtime_wait_ms=0)
        )

        assert sc["ok"] is True
        assert sc["result"]["matched"] is True
        assert sc["result"]["source_used"] == "realtime_buffer"

    @pytest.mark.asyncio
    async def test_markers_mode_filters_weak_success_noise(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools.log import logs_query

        test_logs = [
            "2026-03-19 10:00:00.100  9677  9677 I A02113/com.ohos.FusionSearch: create db store successfully",
            "2026-03-19 10:00:00.200  1059  1384 I C01713/resource_schedule_service/SUSPEND_MANAGER: Thaw pid success.",
        ]

        sc = unwrap_result(await logs_query(logs=test_logs, mode="markers", marker_keywords=["success"]))

        assert sc["ok"] is True
        assert sc["result"]["matched"] is False
        assert sc["result"]["match_count"] == 0
        assert sc["result"]["group_count"] == 0

    @pytest.mark.asyncio
    async def test_markers_mode_does_not_bypass_package_scope_with_broad_marker(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools.log import logs_query

        test_logs = [
            "2026-03-19 10:00:00.100  9677  9677 I A02113/com.ohos.FusionSearch: export completed successfully",
        ]

        sc = unwrap_result(
            await logs_query(
                logs=test_logs,
                mode="markers",
                package_name="com.huawei.securitytool",
                marker_keywords=["completed"],
            )
        )

        assert sc["ok"] is True
        assert sc["result"]["matched"] is False
        assert sc["result"]["match_count"] == 0
        assert sc["result"]["group_count"] == 0

    @pytest.mark.asyncio
    async def test_markers_mode_groups_same_export_file_chain(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools.log import logs_query

        test_logs = [
            "2026-03-19 10:00:00.123  1370  3158 I C0430A/file_monitor_service/file_monitor_service: [WatchInsert] inode: 1, uri: peripheral_policy_list_20260319_153231_2.csv, uid: 100",
            "2026-03-19 10:00:00.223  1370  3158 I C0430A/file_monitor_service/file_monitor_service: [EventProc MODIFY] mask: 8, path: peripheral_policy_list_20260319_153231_2.csv",
            "2026-03-19 10:00:00.323  1700  3051 I C02F36/virus_protection_service/VIRUS_PROTECTION_SERVICE: Start to real-time scan /data/service/el2/100/hmdfs/account/files/Docs/Download/com.huawei.securitytool/peripheral_policy_list_20260319_153231_2.csv",
        ]

        sc = unwrap_result(
            await logs_query(
                logs=test_logs,
                mode="markers",
                package_name="com.huawei.securitytool",
                marker_keywords=["peripheral_policy_list_", "Docs/Download/com.huawei.securitytool", ".csv"],
                context_lines=1,
            )
        )

        assert sc["ok"] is True
        assert sc["result"]["matched"] is True
        assert sc["result"]["match_count"] == 1
        assert sc["result"]["group_count"] == 1
        assert any(
            "Docs/Download/com.huawei.securitytool" in item["message"] or "peripheral_policy_list_" in item["message"]
            for item in sc["result"]["items"]
        )
        assert max(item["score"] for item in sc["result"]["items"]) >= 40

    @pytest.mark.asyncio
    async def test_markers_mode_does_not_merge_same_keyword_across_sources(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools.log import logs_query

        test_logs = [
            "2026-03-19 10:00:00.123  1370  3158 I C0430A/file_monitor_service/file_monitor_service: [WatchInsert] saveResult completed successfully",
            "2026-03-19 10:00:01.123  1700  3051 I C02F36/virus_protection_service/VIRUS_PROTECTION_SERVICE: saveResult completed successfully",
        ]

        sc = unwrap_result(await logs_query(logs=test_logs, mode="markers", marker_keywords=["saveResult"]))

        assert sc["ok"] is True
        assert sc["result"]["match_count"] == 2
        assert sc["result"]["group_count"] == 2
        assert len(sc["result"]["items"]) == 2

    @pytest.mark.asyncio
    async def test_markers_mode_prioritizes_business_specific_match(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools.log import logs_query

        test_logs = [
            "2026-03-19 10:00:00.100  9677  9677 I A02113/com.ohos.FusionSearch: export completed successfully",
            "2026-03-19 10:00:00.200  1700  3051 I C02F36/virus_protection_service/VIRUS_PROTECTION_SERVICE: Start to real-time scan /data/service/el2/100/hmdfs/account/files/Docs/Download/com.huawei.securitytool/peripheral_policy_list_20260319_153231_2.csv",
        ]

        sc = unwrap_result(
            await logs_query(
                logs=test_logs,
                mode="markers",
                package_name="com.huawei.securitytool",
                marker_keywords=["peripheral_policy_list_", "Docs/Download/com.huawei.securitytool", "success"],
            )
        )

        assert sc["ok"] is True
        assert sc["result"]["match_count"] == 1
        assert sc["result"]["group_count"] == 1
        assert "peripheral_policy_list_" in sc["result"]["items"][0]["matched_keywords"]
        assert sc["result"]["items"][0]["score"] >= 40

    @pytest.mark.asyncio
    async def test_realtime_query_samples_multiple_snapshots(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools.log import logs_query

        mock_hdc.get_realtime_logs.side_effect = [
            "2026-03-19 10:00:00.000  1  1 I Tag: before",
            "2026-03-19 10:00:00.100  1  1 I picker: resCode is 0",
            "2026-03-19 10:00:00.200  1  1 I Tag: after",
        ]

        sc = unwrap_result(await logs_query(mode="markers", realtime_wait_ms=3))

        assert sc["ok"] is True
        assert sc["result"]["matched"] is True
        assert sc["result"]["match_count"] == 1
        assert sc["result"]["group_count"] == 1
        assert mock_hdc.get_realtime_logs.call_count == 3

    @pytest.mark.asyncio
    async def test_realtime_miss_does_not_fallback_by_default(self, mock_hdc: MagicMock, monkeypatch, unwrap_result):
        from harmonyos_dev_mcp.tools.log import logs_query, query

        mock_hdc.get_realtime_logs.return_value = "2026-03-19 10:00:00.000  1  1 I Tag: no useful markers"
        historical_called = False

        def _fake_historical(*args, **kwargs):
            nonlocal historical_called
            historical_called = True
            return {"success": True, "raw_lines": [], "dict_used": False, "dict_status": "unavailable", "files_count": 0}

        monkeypatch.setattr(query, "fetch_historical_logs", _fake_historical)

        sc = unwrap_result(await logs_query(mode="markers", realtime_wait_ms=0))

        assert sc["ok"] is True
        assert sc["result"]["matched"] is False
        assert sc["result"]["fallback_triggered"] is False
        assert sc["result"]["group_count"] == 0
        assert historical_called is False

    @pytest.mark.asyncio
    async def test_realtime_miss_can_fallback_to_historical(self, mock_hdc: MagicMock, monkeypatch, unwrap_result):
        from harmonyos_dev_mcp.tools.log import logs_query, query

        mock_hdc.get_realtime_logs.return_value = "2026-03-19 10:00:00.000  1  1 I Tag: no markers"

        def _fake_historical(*args, **kwargs):
            return {
                "success": True,
                "raw_lines": [
                    "2026-03-19 10:00:01.000  1  1 I A03D00/com.huawei.securitytool/JSAPP: saveResult completed successfully"
                ],
                "dict_used": False,
                "dict_status": "unavailable",
                "files_count": 1,
            }

        monkeypatch.setattr(query, "fetch_historical_logs", _fake_historical)

        sc = unwrap_result(
            await logs_query(
                mode="markers",
                package_name="com.huawei.securitytool",
                realtime_wait_ms=0,
                fallback_to_historical=True,
            )
        )

        assert sc["ok"] is True
        assert sc["result"]["matched"] is True
        assert sc["result"]["fallback_triggered"] is True
        assert sc["result"]["source_used"] == "persist_file"
        assert sc["result"]["group_count"] == 1

    @pytest.mark.asyncio
    async def test_explicit_pid_remains_strict(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools.log import logs_query

        test_logs = [
            "2026-03-19 10:00:00.000  1000  1000 I picker: resCode is 0",
            "2026-03-19 10:00:01.000  2000  2000 I picker: resCode is 0",
        ]

        sc = unwrap_result(await logs_query(logs=test_logs, mode="markers", pid=2000))

        assert sc["ok"] is True
        assert sc["result"]["match_count"] == 1
        assert sc["result"]["group_count"] == 1
        assert sc["result"]["items"][0]["pid"] == 2000

    @pytest.mark.asyncio
    async def test_explicit_start_time_prefers_historical_source(self, mock_hdc: MagicMock, monkeypatch, unwrap_result):
        from harmonyos_dev_mcp.tools.log import logs_query, query

        historical_calls = []

        def _fake_historical(*args, **kwargs):
            historical_calls.append((args, kwargs))
            return {
                "success": True,
                "raw_lines": ["2026-03-19 10:00:01.000  1  1 I picker: resCode is 0"],
                "dict_used": False,
                "dict_status": "unavailable",
                "files_count": 1,
            }

        monkeypatch.setattr(query, "fetch_historical_logs", _fake_historical)

        sc = unwrap_result(await logs_query(mode="markers", start_time="2026-03-19 09:00:00"))

        assert sc["ok"] is True
        assert sc["result"]["source_used"] == "persist_file"
        assert historical_calls
        mock_hdc.get_realtime_logs.assert_not_called()
