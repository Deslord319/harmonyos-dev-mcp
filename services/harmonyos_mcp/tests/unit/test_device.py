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
    async def test_fails_when_no_device(self, no_device_mock: MagicMock, unwrap_result):
        from harmonyos_mcp.tools.log import logs_query

        sc = unwrap_result(await logs_query())

        assert sc["ok"] is False
        assert sc["error"]["detail"]
