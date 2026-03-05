"""UI tool tests with standardized MCP response envelope."""

from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.asyncio


class TestClickElement:
    async def test_click_by_coordinates(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_mcp.tools import ui

        sc = unwrap_result(await ui.click_element(x=100, y=200))

        assert sc["ok"] is True
        assert sc["result"]["x"] == 100
        assert sc["result"]["y"] == 200
        mock_ui_operations.click.assert_called_once_with("device_001", 100, 200)

    async def test_click_by_text(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_mcp.tools import ui

        sc = unwrap_result(await ui.click_element(text="登录"))

        assert sc["ok"] is True
        mock_ui_operations.find_element.assert_called_once()
        mock_ui_operations.click.assert_called_once()

    async def test_double_click(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_mcp.tools import ui

        sc = unwrap_result(await ui.click_element(x=100, y=200, double_click=True))

        assert sc["ok"] is True
        mock_ui_operations.double_click.assert_called_once_with("device_001", 100, 200)

    async def test_click_element_not_found(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_mcp.tools import ui

        mock_ui_operations.find_element.return_value = {"success": True, "elements": [], "count": 0}

        sc = unwrap_result(await ui.click_element(text="missing"))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "ELEMENT_NOT_FOUND"

    async def test_click_requires_params(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_mcp.tools import ui

        sc = unwrap_result(await ui.click_element())

        assert sc["ok"] is False
        assert sc["error"]["code"] == "MISSING_PARAMS"


class TestSwipe:
    async def test_swipe_by_coordinates(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_mcp.tools import ui

        sc = unwrap_result(await ui.swipe(from_x=100, from_y=500, to_x=100, to_y=200))

        assert sc["ok"] is True
        mock_ui_operations.swipe.assert_called_once()

    async def test_swipe_by_direction(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_mcp.tools import ui

        sc = unwrap_result(await ui.swipe(direction="up"))

        assert sc["ok"] is True
        mock_ui_operations.swipe_direction.assert_called_once_with("device_001", "up", 600)

    async def test_swipe_with_custom_speed(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_mcp.tools import ui

        sc = unwrap_result(await ui.swipe(direction="down", speed=1000))

        assert sc["ok"] is True
        mock_ui_operations.swipe_direction.assert_called_once_with("device_001", "down", 1000)


class TestInputText:
    async def test_input_by_coordinates(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_mcp.tools import ui

        sc = unwrap_result(await ui.input_text(x=100, y=200, text="Hello World"))

        assert sc["ok"] is True
        mock_ui_operations.input_text.assert_called_once_with("device_001", 100, 200, "Hello World")

    async def test_input_requires_text(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_mcp.tools import ui

        sc = unwrap_result(await ui.input_text(x=100, y=200))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "MISSING_TEXT"


class TestPressKey:
    async def test_press_home(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_mcp.tools import ui

        sc = unwrap_result(await ui.press_key(key="Home"))

        assert sc["ok"] is True
        mock_ui_operations.press_key.assert_called_once_with("device_001", "Home")

    async def test_press_key_requires_key(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_mcp.tools import ui

        sc = unwrap_result(await ui.press_key())

        assert sc["ok"] is False
        assert sc["error"]["code"] == "MISSING_KEY"


class TestFindElement:
    async def test_find_by_text(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_mcp.tools import ui

        sc = unwrap_result(await ui.find_element(text="登录"))

        assert sc["ok"] is True
        assert sc["result"]["count"] == 1
        mock_ui_operations.find_element.assert_called_once()

    async def test_find_by_type(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_mcp.tools import ui

        sc = unwrap_result(await ui.find_element(element_type="Button"))

        assert sc["ok"] is True
        mock_ui_operations.find_element.assert_called_once()

    async def test_find_requires_criteria(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_mcp.tools import ui

        sc = unwrap_result(await ui.find_element())

        assert sc["ok"] is False
        assert sc["error"]["code"] == "MISSING_SEARCH_CRITERIA"
