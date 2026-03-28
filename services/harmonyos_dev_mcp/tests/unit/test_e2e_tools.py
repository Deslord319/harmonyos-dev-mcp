"""Tests for E2E-oriented wait tools."""

from unittest.mock import MagicMock

import pytest

@pytest.mark.asyncio
class TestWaitTools:
    async def test_wait_element_returns_first_match(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result, monkeypatch
    ):
        from harmonyos_dev_mcp.tools import e2e
        monkeypatch.setattr(e2e, "get_ui_operations", lambda: mock_ui_operations)

        sc = unwrap_result(await e2e.wait_element(text="Button", state="found", timeout_ms=10, interval_ms=1))

        assert sc["ok"] is True
        assert sc["result"]["state"] == "found"
        assert sc["result"]["satisfied"] is True
        assert sc["result"]["element"]["id"] == "btn_login"
        assert sc["result"]["element"]["bounds"]["left"] == 80

    async def test_wait_element_found_times_out(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result, monkeypatch
    ):
        from harmonyos_dev_mcp.tools import e2e
        monkeypatch.setattr(e2e, "get_ui_operations", lambda: mock_ui_operations)

        mock_ui_operations.find_element.return_value = {"success": True, "window_id": 1, "elements": [], "count": 0}

        sc = unwrap_result(await e2e.wait_element(text="missing", state="found", timeout_ms=0, interval_ms=0))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "WAIT_TIMEOUT"

    async def test_wait_element_gone_succeeds_when_missing(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result, monkeypatch
    ):
        from harmonyos_dev_mcp.tools import e2e
        monkeypatch.setattr(e2e, "get_ui_operations", lambda: mock_ui_operations)

        mock_ui_operations.find_element.return_value = {"success": True, "window_id": 1, "elements": [], "count": 0}

        sc = unwrap_result(await e2e.wait_element(text="toast", state="gone", timeout_ms=10, interval_ms=1))

        assert sc["ok"] is True
        assert sc["result"]["state"] == "gone"
        assert sc["result"]["satisfied"] is True

    async def test_wait_element_gone_times_out_when_element_still_present(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result, monkeypatch
    ):
        from harmonyos_dev_mcp.tools import e2e
        monkeypatch.setattr(e2e, "get_ui_operations", lambda: mock_ui_operations)

        sc = unwrap_result(await e2e.wait_element(text="toast", state="gone", timeout_ms=0, interval_ms=0))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "WAIT_TIMEOUT"

    async def test_wait_element_rejects_invalid_state(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result, monkeypatch
    ):
        from harmonyos_dev_mcp.tools import e2e
        monkeypatch.setattr(e2e, "get_ui_operations", lambda: mock_ui_operations)

        sc = unwrap_result(await e2e.wait_element(text="toast", state="bad", timeout_ms=0, interval_ms=0))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "INVALID_WAIT_STATE"

    async def test_wait_element_rejects_negative_timeout(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result, monkeypatch
    ):
        from harmonyos_dev_mcp.tools import e2e
        monkeypatch.setattr(e2e, "get_ui_operations", lambda: mock_ui_operations)

        sc = unwrap_result(await e2e.wait_element(text="toast", timeout_ms=-1, interval_ms=0))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "INVALID_TIMEOUT"

    async def test_wait_element_rejects_negative_interval(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result, monkeypatch
    ):
        from harmonyos_dev_mcp.tools import e2e
        monkeypatch.setattr(e2e, "get_ui_operations", lambda: mock_ui_operations)

        sc = unwrap_result(await e2e.wait_element(text="toast", timeout_ms=0, interval_ms=-1))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "INVALID_INTERVAL"

    async def test_wait_element_found_requires_stable_second_observation(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result, monkeypatch
    ):
        from harmonyos_dev_mcp.tools import e2e
        monkeypatch.setattr(e2e, "get_ui_operations", lambda: mock_ui_operations)

        mock_ui_operations.find_element.side_effect = [
            {"success": True, "window_id": 1, "elements": [{"id": "btn_login", "x": 100, "y": 200}], "count": 1},
            {"success": True, "window_id": 1, "elements": [], "count": 0},
            {"success": True, "window_id": 1, "elements": [{"id": "btn_login", "x": 100, "y": 200}], "count": 1},
            {"success": True, "window_id": 1, "elements": [{"id": "btn_login", "x": 100, "y": 200}], "count": 1},
        ]

        sc = unwrap_result(await e2e.wait_element(text="Button", state="found", timeout_ms=50, interval_ms=1))

        assert sc["ok"] is True
        assert sc["result"]["satisfied"] is True

    async def test_wait_element_gone_requires_stable_second_observation(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result, monkeypatch
    ):
        from harmonyos_dev_mcp.tools import e2e
        monkeypatch.setattr(e2e, "get_ui_operations", lambda: mock_ui_operations)

        mock_ui_operations.find_element.side_effect = [
            {"success": True, "window_id": 1, "elements": [], "count": 0},
            {"success": True, "window_id": 1, "elements": [{"id": "toast", "x": 100, "y": 200}], "count": 1},
            {"success": True, "window_id": 1, "elements": [], "count": 0},
            {"success": True, "window_id": 1, "elements": [], "count": 0},
        ]

        sc = unwrap_result(await e2e.wait_element(text="toast", state="gone", timeout_ms=50, interval_ms=1))

        assert sc["ok"] is True
        assert sc["result"]["state"] == "gone"
