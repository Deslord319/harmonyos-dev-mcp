"""Device and log tool tests with standardized MCP response envelope."""

from unittest.mock import MagicMock

import pytest


class TestListDevices:
    @pytest.mark.asyncio
    async def test_returns_device_list(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_mcp.tools import general

        sc = unwrap_result(await general.list_devices())

        assert sc["ok"] is True
        assert sc["result"]["count"] == len(sc["result"]["devices"])
        assert isinstance(sc["result"]["devices"], list)
        if sc["result"]["devices"]:
            assert "device_id" in sc["result"]["devices"][0]

    @pytest.mark.asyncio
    async def test_handles_empty_devices(self, no_device_mock: MagicMock, unwrap_result):
        from harmonyos_mcp.tools import general

        sc = unwrap_result(await general.list_devices())

        assert sc["ok"] is True
        assert sc["result"]["count"] == 0
        assert sc["result"]["devices"] == []

    @pytest.mark.asyncio
    async def test_handles_exception(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_mcp.tools import general

        mock_hdc.list_devices_with_info.side_effect = Exception("Connection failed")

        sc = unwrap_result(await general.list_devices())

        assert sc["ok"] is False
        assert "Connection failed" in sc["error"]["detail"]


class TestQueryPackage:
    @pytest.mark.asyncio
    async def test_main_ability_uses_recommended_candidate_fields(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_mcp.tools import general

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
        from harmonyos_mcp.tools import general

        mock_hdc.get_package_permissions.return_value = {
            "success": True,
            "requested_permissions": ["ohos.permission.INTERNET"],
            "permission_count": 1,
        }

        sc = unwrap_result(await general.query_package(bundle_name="com.example.app", info_type="permissions"))

        assert sc["ok"] is True
        assert sc["result"]["requested_permissions"] == ["ohos.permission.INTERNET"]
        assert sc["result"]["permission_count"] == 1


class TestUiTree:
    @pytest.mark.asyncio
    async def test_list_windows_maps_rect_to_bounds(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_mcp.tools import ui_tree

        sc = unwrap_result(await ui_tree.list_windows())

        assert sc["ok"] is True
        window = sc["result"]["windows"][0]
        assert window["bounds"] == {"left": 10, "top": 20, "right": 310, "bottom": 420}
        assert window["bundle_name_resolved"] is True

    @pytest.mark.asyncio
    async def test_list_windows_filters_by_bundle_name(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_mcp.tools import ui_tree

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

        sc = unwrap_result(await ui_tree.list_windows(bundle_name="com.huawei.hmos.settings"))

        assert sc["ok"] is True
        assert sc["result"]["count"] == 1
        assert sc["result"]["windows"][0]["bundle_name"] == "com.huawei.hmos.settings"

    @pytest.mark.asyncio
    async def test_list_windows_bundle_filter_can_return_empty(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_mcp.tools import ui_tree

        sc = unwrap_result(await ui_tree.list_windows(bundle_name="com.example.missing"))

        assert sc["ok"] is True
        assert sc["result"]["count"] == 0
        assert sc["result"]["windows"] == []

    @pytest.mark.asyncio
    async def test_list_windows_marks_unresolved_bundle_name(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_mcp.tools import ui_tree

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

        sc = unwrap_result(await ui_tree.list_windows())

        assert sc["ok"] is True
        window = sc["result"]["windows"][0]
        assert window["bundle_name"] == ""
        assert window["bundle_name_resolved"] is False
        assert window["bounds"] == {"left": 1, "top": 2, "right": 4, "bottom": 6}

    @pytest.mark.asyncio
    async def test_list_windows_returns_parse_error(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_mcp.tools import ui_tree

        mock_hdc.get_window_list.return_value = {
            "success": False,
            "error_code": "LIST_WINDOWS_PARSE_ERROR",
            "error": "failed to parse window list header",
            "windows": [],
        }

        sc = unwrap_result(await ui_tree.list_windows())

        assert sc["ok"] is False
        assert sc["error"]["code"] == "LIST_WINDOWS_PARSE_ERROR"

    @pytest.mark.asyncio
    async def test_get_ui_tree_returns_list_windows_error_when_window_query_fails_for_targeted_lookup(
        self, mock_hdc: MagicMock, unwrap_result
    ):
        from harmonyos_mcp.tools import ui_tree

        mock_hdc.get_window_list.return_value = {"success": False, "error": "wm failed", "error_code": "LIST_WINDOWS_ERROR"}

        sc = unwrap_result(await ui_tree.get_ui_tree(bundle_name="com.example.app"))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "LIST_WINDOWS_ERROR"
        assert sc["error"]["detail"] == "wm failed"

    @pytest.mark.asyncio
    async def test_get_ui_tree_returns_no_windows_when_targeted_lookup_window_list_empty(
        self, mock_hdc: MagicMock, unwrap_result
    ):
        from harmonyos_mcp.tools import ui_tree

        mock_hdc.get_window_list.return_value = {"success": True, "windows": [], "count": 0}

        sc = unwrap_result(await ui_tree.get_ui_tree(bundle_name="com.example.app"))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "NO_WINDOWS"

    @pytest.mark.asyncio
    async def test_get_ui_tree_without_target_does_not_query_windows(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_mcp.tools import ui_tree

        sc = unwrap_result(await ui_tree.get_ui_tree())

        assert sc["ok"] is True
        mock_hdc.get_window_list.assert_not_called()
        mock_hdc.get_ui_tree_raw.assert_called_once_with("device_001", None)

    @pytest.mark.asyncio
    async def test_get_ui_tree_with_bundle_name_validates_target_window(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_mcp.tools import ui_tree

        sc = unwrap_result(await ui_tree.get_ui_tree(bundle_name="com.example.app"))

        assert sc["ok"] is True
        mock_hdc.get_window_list.assert_called_once_with("device_001")
        mock_hdc.get_ui_tree_raw.assert_called_once_with("device_001", 1)

    @pytest.mark.asyncio
    async def test_get_ui_tree_rejects_bundle_when_not_explicitly_resolved(
        self, mock_hdc: MagicMock, unwrap_result
    ):
        from harmonyos_mcp.tools import ui_tree

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

        sc = unwrap_result(await ui_tree.get_ui_tree(bundle_name="com.example.app"))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "WINDOW_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_ui_tree_with_window_id_validates_window_exists(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_mcp.tools import ui_tree

        sc = unwrap_result(await ui_tree.get_ui_tree(window_id=1))

        assert sc["ok"] is True
        mock_hdc.get_window_list.assert_called_once_with("device_001")
        mock_hdc.get_ui_tree_raw.assert_called_once_with("device_001", 1)

    @pytest.mark.asyncio
    async def test_get_ui_tree_rejects_unknown_window_id(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_mcp.tools import ui_tree

        sc = unwrap_result(await ui_tree.get_ui_tree(window_id=999))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "WINDOW_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_ui_tree_rejects_window_bundle_mismatch(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_mcp.tools import ui_tree

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

        sc = unwrap_result(await ui_tree.get_ui_tree(bundle_name="com.example.app", window_id=7))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "WINDOW_BUNDLE_MISMATCH"


class TestLogsQuery:
    @pytest.mark.asyncio
    async def test_direct_logs_input(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_mcp.tools.log import logs_query

        test_logs = [
            "01-31 10:00:00.123  1000  2000 E MyApp: test error",
            "01-31 10:00:01.456  1000  2000 I MyApp: test info",
        ]
        sc = unwrap_result(await logs_query(logs=test_logs))

        assert sc["ok"] is True
        assert sc["result"]["source"] == "direct"
        assert len(sc["result"]["findings"]) == 1

    @pytest.mark.asyncio
    async def test_level_filter(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_mcp.tools.log import logs_query

        test_logs = [
            "01-31 10:00:00.123  1000  2000 E MyApp: error",
            "01-31 10:00:01.456  1000  2000 I MyApp: info",
            "01-31 10:00:02.789  1000  2000 W MyApp: warning",
        ]
        sc = unwrap_result(await logs_query(logs=test_logs, level="E"))

        assert sc["ok"] is True
        assert len(sc["result"]["findings"]) == 1

    @pytest.mark.asyncio
    async def test_seconds_accepts_numeric_string(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_mcp.tools.log import logs_query

        test_logs = [
            "01-31 10:00:00.123  1000  2000 E MyApp: error",
            "01-31 10:00:01.456  1000  2000 I MyApp: info",
        ]
        sc = unwrap_result(await logs_query(logs=test_logs, seconds="30"))

        assert sc["ok"] is True
        assert sc["result"]["filters_applied"]["seconds"] == 30

    @pytest.mark.asyncio
    async def test_fails_when_no_device(self, no_device_mock: MagicMock, unwrap_result):
        from harmonyos_mcp.tools.log import logs_query

        sc = unwrap_result(await logs_query())

        assert sc["ok"] is False
        assert sc["error"]["detail"]

    @pytest.mark.asyncio
    async def test_package_name_requires_running_app(self, mock_hdc: MagicMock, unwrap_result):
        from harmonyos_mcp.tools.log import logs_query

        mock_hdc.get_app_pid.return_value = None

        sc = unwrap_result(await logs_query(package_name="com.huawei.securitytool"))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "APP_NOT_RUNNING"
        assert "requires the target app to be running" in sc["error"]["detail"]
