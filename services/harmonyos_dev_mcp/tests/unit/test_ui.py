"""UI tool tests with standardized MCP response envelope."""

from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.asyncio


def _sample_handle(*, with_lookup_hint: bool = True) -> dict:
    handle = {
        "window_id": 1,
        "id": "btn_login",
        "compid": "comp_btn_login",
        "type": "Button",
        "text": "Button",
        "x": 100,
        "y": 200,
        "bounds": {"left": 80, "top": 180, "right": 120, "bottom": 220},
        "bundle_name": "com.example.app",
    }
    if with_lookup_hint:
        handle["lookup_hint"] = {"text": "Button", "element_type": "Button", "bundle_name": "com.example.app", "window_id": 1}
    return handle


class TestClickElement:
    async def test_click_by_coordinates(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.click_element(x=100, y=200))

        assert sc["ok"] is True
        assert sc["result"]["message"] == "click succeeded"
        assert sc["result"]["x"] == 100
        assert sc["result"]["y"] == 200
        assert sc["result"]["resolved_via"] == "coordinates"

    async def test_click_by_text(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.click_element(text="登录"))

        assert sc["ok"] is True
        assert sc["result"]["resolved_via"] == "search"
        mock_ui_operations.find_element.assert_called_once()
        mock_ui_operations.click.assert_called_once()

    async def test_click_by_element_id(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.click_element(element_id="btn_login"))

        assert sc["ok"] is True
        assert sc["result"]["resolved_via"] == "search"
        mock_ui_operations.find_element.assert_called_once()

    async def test_click_by_handle(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.click_element(element_handle=_sample_handle()))

        assert sc["ok"] is True
        assert sc["result"]["resolved_via"] == "handle"
        assert sc["result"]["handle_refreshed"] is False
        assert sc["result"]["element_handle"]["compid"] == "comp_btn_login"
        mock_ui_operations.click.assert_called_once_with("device_001", 100, 200)

    async def test_click_stale_handle_retries_once(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        mock_ui_operations.find_element.side_effect = [
            {"success": True, "window_id": 1, "elements": [], "count": 0},
            {
                "success": True,
                "window_id": 1,
                "elements": [
                    {
                        "id": "btn_login_new",
                        "compid": "comp_btn_login_new",
                        "x": 140,
                        "y": 240,
                        "left": 120,
                        "top": 220,
                        "width": 40,
                        "height": 40,
                        "text": "Button",
                        "type": "Button",
                    }
                ],
                "count": 1,
            },
        ]

        sc = unwrap_result(await ui.click_element(element_handle=_sample_handle()))

        assert sc["ok"] is True
        assert sc["result"]["resolved_via"] == "lookup_hint"
        assert sc["result"]["handle_refreshed"] is True
        assert sc["result"]["element_handle"]["compid"] == "comp_btn_login_new"
        mock_ui_operations.click.assert_called_once_with("device_001", 140, 240)

    async def test_click_stale_handle_without_lookup_hint_fails(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import ui

        mock_ui_operations.find_element.return_value = {"success": True, "window_id": 1, "elements": [], "count": 0}

        sc = unwrap_result(await ui.click_element(element_handle=_sample_handle(with_lookup_hint=False)))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "ELEMENT_NOT_FOUND"

    async def test_click_stale_handle_with_ambiguous_retry_fails(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import ui

        mock_ui_operations.find_element.side_effect = [
            {"success": True, "window_id": 1, "elements": [], "count": 0},
            {
                "success": True,
                "window_id": 1,
                "elements": [
                    {"id": "a", "compid": "a", "x": 100, "y": 200, "text": "Button", "type": "Button"},
                    {"id": "b", "compid": "b", "x": 120, "y": 220, "text": "Button", "type": "Button"},
                ],
                "count": 2,
            },
        ]

        sc = unwrap_result(await ui.click_element(element_handle=_sample_handle()))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "AMBIGUOUS_ELEMENT_MATCH"
        assert "more specific text" in sc["error"]["detail"]
        assert sc["result"]["match_count"] == 2
        assert len(sc["result"]["candidate_handles"]) == 2
        assert sc["result"]["candidate_handles"][0]["compid"] == "a"

    async def test_double_click(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.click_element(x=100, y=200, double_click=True))

        assert sc["ok"] is True
        assert sc["result"]["message"] == "double click succeeded"
        mock_ui_operations.double_click.assert_called_once_with("device_001", 100, 200)

    async def test_click_element_not_found(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        mock_ui_operations.find_element.return_value = {"success": True, "elements": [], "count": 0}

        sc = unwrap_result(await ui.click_element(text="missing"))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "ELEMENT_NOT_FOUND"

    async def test_click_requires_params(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.click_element())

        assert sc["ok"] is False
        assert sc["error"]["code"] == "MISSING_PARAMS"

    async def test_click_rejects_coordinate_conflict(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.click_element(x=100, y=200, element_handle=_sample_handle()))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "PARAM_CONFLICT"


class TestSwipe:
    async def test_swipe_by_coordinates(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.swipe(from_x=100, from_y=500, to_x=100, to_y=200))

        assert sc["ok"] is True
        assert sc["result"]["message"] == "swipe succeeded"
        mock_ui_operations.swipe.assert_called_once()

    async def test_swipe_by_direction(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.swipe(direction="up"))

        assert sc["ok"] is True
        assert sc["result"]["message"] == "swipe succeeded"
        mock_ui_operations.swipe_direction.assert_called_once_with("device_001", "up", 600)

    async def test_swipe_with_custom_speed(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.swipe(direction="down", speed=1000))

        assert sc["ok"] is True
        mock_ui_operations.swipe_direction.assert_called_once_with("device_001", "down", 1000)

    async def test_swipe_rejects_direction_coordinate_conflict(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.swipe(direction="up", from_x=1, from_y=2, to_x=3, to_y=4))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "PARAM_CONFLICT"


class TestInputText:
    async def test_input_rejects_json_string_handle(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(
            await ui.input_text(element_handle='{"window_id":1,"id":"btn_login"}', text="Hello World")
        )

        assert sc["ok"] is False
        assert sc["error"]["code"] == "INVALID_ELEMENT_HANDLE"
        assert "Do not pass a JSON string" in sc["error"]["detail"]

    async def test_input_by_coordinates(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.input_text(x=100, y=200, text="Hello World"))

        assert sc["ok"] is True
        assert sc["result"]["message"] == "input text succeeded"
        assert sc["result"]["resolved_via"] == "coordinates"
        mock_ui_operations.input_text.assert_called_once_with("device_001", 100, 200, "Hello World")

    async def test_input_by_lookup(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.input_text(element_type="TextInput", text="Hello World"))

        assert sc["ok"] is True
        assert sc["result"]["resolved_via"] == "search"
        mock_ui_operations.find_element.assert_called_once()
        mock_ui_operations.input_text.assert_called_once()

    async def test_input_by_element_id(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.input_text(element_id="btn_login", text="Hello World"))

        assert sc["ok"] is True
        assert sc["result"]["resolved_via"] == "search"

    async def test_input_by_handle(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.input_text(element_handle=_sample_handle(), text="Hello World"))

        assert sc["ok"] is True
        assert sc["result"]["resolved_via"] == "handle"
        assert sc["result"]["handle_refreshed"] is False
        mock_ui_operations.input_text.assert_called_once_with("device_001", 100, 200, "Hello World")

    async def test_input_requires_text(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.input_text(x=100, y=200))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "MISSING_TEXT"

    async def test_input_requires_target(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.input_text(text="Hello World"))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "MISSING_PARAMS"

    async def test_input_lookup_not_found_is_actionable(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        mock_ui_operations.find_element.return_value = {"success": True, "elements": [], "count": 0}

        sc = unwrap_result(await ui.input_text(element_type="TextInput", text="Hello World"))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "ELEMENT_NOT_FOUND"
        assert "use x/y for a stable path" in sc["error"]["detail"]

    async def test_input_rejects_coordinate_conflict(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.input_text(x=100, y=200, text="Hello", element_handle=_sample_handle()))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "PARAM_CONFLICT"


class TestPressKey:
    async def test_press_home(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.press_key(key="Home"))

        assert sc["ok"] is True
        assert sc["result"]["message"] == "key press succeeded"
        mock_ui_operations.press_key.assert_called_once_with("device_001", "Home")

    async def test_press_key_requires_key(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.press_key())

        assert sc["ok"] is False
        assert sc["error"]["code"] == "MISSING_KEY"


class TestFindElement:
    async def test_find_by_text(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.find_element(text="登录"))

        assert sc["ok"] is True
        assert sc["result"]["count"] == 1
        mock_ui_operations.find_element.assert_called_once()

    async def test_find_by_type(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.find_element(element_type="Button"))

        assert sc["ok"] is True
        assert sc["result"]["elements"][0]["lookup_is_broad"] is True
        mock_ui_operations.find_element.assert_called_once()

    async def test_find_includes_handle_metadata(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.find_element(text="Button", bundle_name="com.example.app"))

        assert sc["ok"] is True
        element = sc["result"]["elements"][0]
        assert element["element_handle"]["compid"] == "comp_btn_login"
        assert element["element_handle"]["lookup_hint"]["text"] == "Button"
        assert element["lookup_is_broad"] is False
        assert "lookup_hint" not in element
        assert element["bounds"]["left"] == 80

    async def test_find_requires_criteria(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.find_element())

        assert sc["ok"] is False
        assert sc["error"]["code"] == "MISSING_SEARCH_CRITERIA"

    async def test_find_returns_not_found_when_empty(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        mock_ui_operations.find_element.return_value = {"success": True, "elements": [], "count": 0}

        sc = unwrap_result(await ui.find_element(text="missing"))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "ELEMENT_NOT_FOUND"
        assert sc["result"]["count"] == 0


class TestLongPressElement:
    async def test_long_press_by_handle(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.long_press_element(element_handle=_sample_handle()))

        assert sc["ok"] is True
        assert sc["result"]["resolved_via"] == "handle"
        mock_ui_operations.long_click.assert_called_once_with("device_001", 100, 200)

    async def test_long_press_by_element_id(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.long_press_element(element_id="btn_login"))

        assert sc["ok"] is True
        assert sc["result"]["resolved_via"] == "search"


class TestScreenshot:
    async def test_screenshot_rejects_partial_bounds(self, mock_hdc: MagicMock, unwrap_result, monkeypatch):
        from harmonyos_dev_mcp.tools import ui

        monkeypatch.setattr(ui, "get_hdc", lambda: mock_hdc)
        sc = unwrap_result(await ui.screenshot(left=0, top=0, right=100))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "PARAM_CONFLICT"
