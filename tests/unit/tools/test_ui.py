"""UI tool tests with standardized MCP response envelope."""

import asyncio
from copy import deepcopy
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


class TestClick:
    async def test_click_by_coordinates(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.click(x=100, y=200))

        assert sc["ok"] is True
        assert sc["result"]["message"] == "click dispatched"
        assert sc["result"]["dispatched"] is True
        assert sc["result"]["effect_verified"] is False
        assert sc["result"]["x"] == 100
        assert sc["result"]["y"] == 200
        assert sc["result"]["count"] == 1
        assert sc["result"]["resolved_via"] == "coordinates"
        assert "action" not in sc["result"]

    async def test_click_by_text(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.click(text="登录"))

        assert sc["ok"] is True
        assert sc["result"]["resolved_via"] == "search"
        mock_ui_operations.find_element.assert_called_once()
        mock_ui_operations.click.assert_called_once()

    async def test_click_by_element_id(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.click(element_id="btn_login"))

        assert sc["ok"] is True
        assert sc["result"]["resolved_via"] == "search"
        mock_ui_operations.find_element.assert_called_once()

    async def test_click_by_handle(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.click(element_handle=_sample_handle()))

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

        sc = unwrap_result(await ui.click(element_handle=_sample_handle()))

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

        sc = unwrap_result(await ui.click(element_handle=_sample_handle(with_lookup_hint=False)))

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

        sc = unwrap_result(await ui.click(element_handle=_sample_handle()))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "AMBIGUOUS_ELEMENT_MATCH"
        assert "more specific text" in sc["error"]["detail"]
        assert sc["result"]["match_count"] == 2
        assert len(sc["result"]["candidate_handles"]) == 2
        assert sc["result"]["candidate_handles"][0]["compid"] == "a"

    async def test_double_click(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.click(x=100, y=200, count=2))

        assert sc["ok"] is True
        assert sc["result"]["message"] == "double click dispatched"
        assert sc["result"]["dispatched"] is True
        assert sc["result"]["effect_verified"] is False
        assert sc["result"]["count"] == 2
        mock_ui_operations.double_click.assert_called_once_with("device_001", 100, 200)

    async def test_click_not_found(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        mock_ui_operations.find_element.return_value = {"success": True, "elements": [], "count": 0}

        sc = unwrap_result(await ui.click(text="missing"))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "ELEMENT_NOT_FOUND"

    async def test_click_requires_params(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.click())

        assert sc["ok"] is False
        assert sc["error"]["code"] == "MISSING_PARAMS"

    async def test_click_rejects_coordinate_conflict(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.click(x=100, y=200, element_handle=_sample_handle()))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "PARAM_CONFLICT"

    async def test_click_rejects_invalid_count(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.click(x=100, y=200, count=3))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "INVALID_CLICK_COUNT"

    async def test_click_failure_reports_not_dispatched(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import ui

        mock_ui_operations.click.return_value = {
            "success": False,
            "error": "device rejected click",
        }

        sc = unwrap_result(await ui.click(x=100, y=200))

        assert sc["ok"] is False
        assert sc["result"]["dispatched"] is False
        assert sc["result"]["effect_verified"] is False


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
    @pytest.fixture(autouse=True)
    def short_input_verification_deadline(self, monkeypatch):
        from harmonyos_dev_mcp.config import Config

        monkeypatch.setattr(Config, "INPUT_FOCUS_TIMEOUT_MS", 20)
        monkeypatch.setattr(Config, "INPUT_VERIFY_TIMEOUT_MS", 20)

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
        assert sc["result"]["message"] == "input text dispatched without verification"
        assert sc["result"]["resolved_via"] == "coordinates"
        assert sc["result"]["mode"] == "replace"
        assert sc["result"]["dispatched"] is True
        assert sc["result"]["verified"] is False
        assert sc["result"]["input_strategy"] == "best_effort_direct"
        assert sc["result"]["clipboard_modified"] is False
        mock_ui_operations.replace_text.assert_called_once_with("device_001", 100, 200, "Hello World")

    async def test_input_can_append_text(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.input_text(x=100, y=200, text="Hello", mode="append"))

        assert sc["ok"] is True
        assert sc["result"]["mode"] == "append"
        mock_ui_operations.input_text.assert_called_once_with("device_001", 100, 200, "Hello")

    async def test_input_by_lookup(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        initial = deepcopy(mock_ui_operations.find_element.return_value)
        updated = deepcopy(initial)
        updated["elements"][0]["text"] = "Hello World"
        mock_ui_operations.find_element.side_effect = [initial, initial, updated]

        sc = unwrap_result(await ui.input_text(element_type="TextInput", text="Hello World"))

        assert sc["ok"] is True
        assert sc["result"]["resolved_via"] == "search"
        assert sc["result"]["verified"] is True
        assert mock_ui_operations.find_element.call_count == 3
        mock_ui_operations.replace_focused_text.assert_called_once()

    async def test_input_by_element_id(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        initial = deepcopy(mock_ui_operations.find_element.return_value)
        updated = deepcopy(initial)
        updated["elements"][0]["text"] = "Hello World"
        mock_ui_operations.find_element.side_effect = [initial, initial, updated]

        sc = unwrap_result(await ui.input_text(element_id="btn_login", text="Hello World"))

        assert sc["ok"] is True
        assert sc["result"]["resolved_via"] == "search"

    async def test_input_by_handle(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        initial = deepcopy(mock_ui_operations.find_element.return_value)
        updated = deepcopy(initial)
        updated["elements"][0]["text"] = "Hello World"
        mock_ui_operations.find_element.side_effect = [initial, initial, updated]

        sc = unwrap_result(await ui.input_text(element_handle=_sample_handle(), text="Hello World"))

        assert sc["ok"] is True
        assert sc["result"]["resolved_via"] == "handle"
        assert sc["result"]["handle_refreshed"] is False
        assert sc["result"]["verified"] is True
        assert sc["result"]["actual_text"] == "Hello World"
        assert sc["result"]["cleanup_performed"] is False
        mock_ui_operations.replace_focused_text.assert_called_once_with("device_001", 100, 200, "Hello World中")

    async def test_input_forced_paste_removes_only_observed_sentinel(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import ui
        from harmonyos_dev_mcp.ui.keycodes import KeyCode

        initial = deepcopy(mock_ui_operations.find_element.return_value)
        with_sentinel = deepcopy(initial)
        with_sentinel["elements"][0]["text"] = "AgentABC09中"
        cleaned = deepcopy(initial)
        cleaned["elements"][0]["text"] = "AgentABC09"
        mock_ui_operations.find_element.side_effect = [initial, initial, with_sentinel, cleaned]

        sc = unwrap_result(await ui.input_text(element_handle=_sample_handle(), text="AgentABC09"))

        assert sc["ok"] is True
        assert sc["result"]["input_strategy"] == "forced_paste_sentinel"
        assert sc["result"]["clipboard_modified"] is True
        assert sc["result"]["cleanup_performed"] is True
        assert sc["result"]["actual_text"] == "AgentABC09"
        mock_ui_operations.press_key.assert_called_once_with("device_001", int(KeyCode.DEL))

    async def test_input_reports_cleanup_failure_after_observing_sentinel(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import ui

        initial = deepcopy(mock_ui_operations.find_element.return_value)
        with_sentinel = deepcopy(initial)
        with_sentinel["elements"][0]["text"] = "Agent中"
        mock_ui_operations.find_element.side_effect = [initial, initial, with_sentinel]
        mock_ui_operations.press_key.return_value = {
            "success": False,
            "error": "Backspace rejected",
        }

        sc = unwrap_result(await ui.input_text(element_handle=_sample_handle(), text="Agent"))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "TEXT_CLEANUP_FAILED"
        assert sc["result"]["actual_text"] == "Agent中"
        assert sc["result"]["cleanup_performed"] is False
        assert sc["result"]["stage"] == "cleanup"

    async def test_input_verifies_composite_component_via_subtree(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result
    ):
        """Composite components (e.g. Search) keep the editable value in a
        descendant while the resolved element's own text stays empty.
        Verification must read the subtree, and sentinel cleanup must fire
        against the subtree value instead of the empty parent."""
        import json as _json

        from harmonyos_dev_mcp.tools import ui
        from harmonyos_dev_mcp.ui.keycodes import KeyCode

        search_element = {
            "id": "41",
            "compid": "588:41",
            "type": "Search",
            "text": "",
            "x": 100,
            "y": 200,
            "window_id": 1,
            "focused": True,
            "visible": True,
            "enabled": True,
            "clickable": True,
            "bounds": {"left": 80, "top": 180, "right": 120, "bottom": 220},
        }
        mock_ui_operations.find_element.return_value = {
            "success": True,
            "window_id": 1,
            "elements": [search_element],
        }

        def _ui_tree(child_text: str) -> str:
            return _json.dumps(
                {
                    "children": [
                        {
                            "attributes": {
                                "type": "Search",
                                "hashcode": "588:41",
                                "text": "",
                                "accessibilityId": "41",
                                "bounds": "[80,180][120,220]",
                                "focused": "true",
                                "visible": "true",
                            },
                            "children": [
                                {
                                    "attributes": {
                                        "type": "SearchField",
                                        "hashcode": "588:42",
                                        "text": child_text,
                                        "accessibilityId": "42",
                                        "bounds": "[80,180][120,220]",
                                        "focused": "true",
                                    },
                                    "children": [],
                                }
                            ],
                        }
                    ]
                }
            )

        mock_hdc.get_ui_tree_raw.side_effect = [
            {"success": True, "ui_tree": _ui_tree("wifi中")},
            {"success": True, "ui_tree": _ui_tree("wifi")},
        ]

        handle = _sample_handle(with_lookup_hint=True)
        handle.update(
            {
                "id": "41",
                "compid": "588:41",
                "type": "Search",
                "text": "",
            }
        )

        sc = unwrap_result(await ui.input_text(element_handle=handle, text="wifi"))

        assert sc["ok"] is True
        assert sc["result"]["verified"] is True
        assert sc["result"]["actual_text"] == "wifi"
        assert sc["result"]["cleanup_performed"] is True
        assert sc["result"]["input_strategy"] == "forced_paste_sentinel"
        mock_ui_operations.replace_focused_text.assert_called_once_with(
            "device_001", 100, 200, "wifi中"
        )
        mock_ui_operations.press_key.assert_called_once_with("device_001", int(KeyCode.DEL))

    async def test_input_observes_until_ui_tree_reaches_expected_text(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import ui

        initial = deepcopy(mock_ui_operations.find_element.return_value)
        updated = deepcopy(initial)
        updated["elements"][0]["text"] = "42"
        mock_ui_operations.find_element.side_effect = [initial, initial, initial, updated]

        sc = unwrap_result(await ui.input_text(element_handle=_sample_handle(), text="42"))

        assert sc["ok"] is True
        assert sc["result"]["observations"] == 2
        assert sc["result"]["input_strategy"] == "direct_key_events"
        assert sc["result"]["clipboard_modified"] is False
        mock_ui_operations.replace_focused_text.assert_called_once_with("device_001", 100, 200, "42")

    async def test_input_unicode_uses_native_paste_without_sentinel(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import ui

        text = "中文Agent09"
        sc = unwrap_result(await ui.input_text(x=100, y=200, text=text))

        assert sc["ok"] is True
        assert sc["result"]["input_strategy"] == "native_paste"
        assert sc["result"]["clipboard_modified"] is True
        mock_ui_operations.replace_text.assert_called_once_with("device_001", 100, 200, text)

    async def test_long_numeric_text_uses_native_paste_route(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import ui

        text = "7" * 201
        sc = unwrap_result(await ui.input_text(x=100, y=200, text=text))

        assert sc["ok"] is True
        assert sc["result"]["input_strategy"] == "native_paste"
        assert sc["result"]["clipboard_modified"] is True
        mock_ui_operations.replace_text.assert_called_once_with("device_001", 100, 200, text)

    async def test_append_verifies_exact_previous_plus_requested_text(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import ui

        initial = deepcopy(mock_ui_operations.find_element.return_value)
        initial["elements"][0]["text"] = "Base"
        updated = deepcopy(initial)
        updated["elements"][0]["text"] = "BaseHello"
        mock_ui_operations.find_element.side_effect = [initial, initial, updated]

        sc = unwrap_result(
            await ui.input_text(element_handle=_sample_handle(), text="Hello", mode="append")
        )

        assert sc["ok"] is True
        assert sc["result"]["before_text"] == "Base"
        assert sc["result"]["actual_text"] == "BaseHello"
        mock_ui_operations.input_focused_text.assert_called_once_with("device_001", 100, 200, "Hello中")

    async def test_append_does_not_accept_an_unrelated_matching_suffix(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import ui

        initial = deepcopy(mock_ui_operations.find_element.return_value)
        initial["elements"][0]["text"] = "Base"
        wrong = deepcopy(initial)
        wrong["elements"][0]["text"] = "OtherHello"
        responses = iter([initial, initial])

        def find_element(*args, **kwargs):
            return next(responses, wrong)

        mock_ui_operations.find_element.side_effect = find_element

        sc = unwrap_result(
            await ui.input_text(element_handle=_sample_handle(), text="Hello", mode="append")
        )

        assert sc["ok"] is False
        assert sc["error"]["code"] == "TEXT_VERIFICATION_TIMEOUT"
        assert sc["result"]["before_text"] == "Base"
        assert sc["result"]["actual_text"] == "OtherHello"
        mock_ui_operations.press_key.assert_not_called()

    async def test_append_requires_readable_existing_text(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import ui

        initial = deepcopy(mock_ui_operations.find_element.return_value)
        initial["elements"][0].pop("text", None)
        mock_ui_operations.find_element.return_value = initial

        sc = unwrap_result(
            await ui.input_text(element_handle=_sample_handle(), text="Hello", mode="append")
        )

        assert sc["ok"] is False
        assert sc["error"]["code"] == "TEXT_NOT_READABLE"
        assert sc["result"]["stage"] == "resolve_target"
        mock_ui_operations.input_text.assert_not_called()

    async def test_empty_replace_clears_and_verifies(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import ui

        initial = deepcopy(mock_ui_operations.find_element.return_value)
        cleared = deepcopy(initial)
        cleared["elements"][0]["text"] = ""
        mock_ui_operations.find_element.side_effect = [initial, initial, cleared]

        sc = unwrap_result(await ui.input_text(element_handle=_sample_handle(), text=""))

        assert sc["ok"] is True
        assert sc["result"]["input_strategy"] == "clear"
        assert sc["result"]["actual_text"] == ""
        mock_ui_operations.replace_focused_text.assert_called_once_with("device_001", 100, 200, "")

    async def test_input_by_handle_rejects_false_command_success(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.input_text(element_handle=_sample_handle(), text="Hello World"))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "TEXT_VERIFICATION_TIMEOUT"
        assert sc["result"]["verified"] is False
        assert sc["result"]["actual_text"] == "Button"
        mock_ui_operations.press_key.assert_not_called()

    async def test_input_dispatch_failure_reports_stage_without_verifying(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import ui

        mock_ui_operations.replace_focused_text.return_value = {
            "success": False,
            "stage": "dispatch",
            "error": "uitest rejected text",
        }

        sc = unwrap_result(await ui.input_text(element_handle=_sample_handle(), text="Hello"))

        assert sc["ok"] is False
        assert sc["result"]["dispatched"] is False
        assert sc["result"]["verified"] is False
        assert sc["result"]["stage"] == "dispatch"
        assert mock_ui_operations.find_element.call_count == 2

    async def test_input_search_rejects_ambiguous_target(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import ui

        raw = deepcopy(mock_ui_operations.find_element.return_value)
        second = deepcopy(raw["elements"][0])
        second["id"] = "second"
        second["compid"] = "second"
        second["x"] = 120
        raw["elements"].append(second)
        raw["count"] = 2
        mock_ui_operations.find_element.return_value = raw

        sc = unwrap_result(await ui.input_text(element_type="TextInput", text="Hello"))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "AMBIGUOUS_ELEMENT_MATCH"
        mock_ui_operations.replace_text.assert_not_called()

    async def test_input_requires_text(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.input_text(x=100, y=200, text=None))

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
        assert "pass its element_handle" in sc["error"]["detail"]

    async def test_input_rejects_coordinate_conflict(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.input_text(x=100, y=200, text="Hello", element_handle=_sample_handle()))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "PARAM_CONFLICT"

    async def test_input_waits_for_foreground_focus_before_dispatch(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import ui

        initial = deepcopy(mock_ui_operations.find_element.return_value)
        initial["elements"][0]["focused"] = False
        focused = deepcopy(initial)
        focused["elements"][0]["focused"] = True
        updated = deepcopy(focused)
        updated["elements"][0]["text"] = "42"
        mock_ui_operations.find_element.side_effect = [initial, focused, focused, updated]
        background_windows = {
            "success": True,
            "windows": [
                {
                    "window_id": 1,
                    "bundle_name": "com.example.app",
                    "is_visible": True,
                    "display_id": 0,
                    "type": 1,
                    "zord": 100,
                },
                {
                    "window_id": 2,
                    "bundle_name": "com.example.front",
                    "is_visible": True,
                    "display_id": 0,
                    "type": 1,
                    "zord": 101,
                },
            ],
        }
        foreground_windows = deepcopy(background_windows)
        foreground_windows["windows"][0]["zord"] = 102
        mock_hdc.get_window_list.side_effect = [background_windows, foreground_windows]

        sc = unwrap_result(await ui.input_text(element_handle=_sample_handle(), text="42"))

        assert sc["ok"] is True
        assert sc["result"]["focus_dispatched"] is True
        assert sc["result"]["focus_verified"] is True
        assert sc["result"]["focus_observations"] == 2
        assert sc["result"]["window_foreground"] is True
        assert sc["result"]["foreground_window_id"] == 1
        mock_ui_operations.replace_focused_text.assert_called_once()

    async def test_input_does_not_dispatch_text_to_background_window(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import ui

        mock_hdc.get_window_list.return_value = {
            "success": True,
            "windows": [
                {
                    "window_id": 1,
                    "bundle_name": "com.example.app",
                    "is_visible": True,
                    "display_id": 0,
                    "type": 1,
                    "zord": 100,
                },
                {
                    "window_id": 2,
                    "bundle_name": "com.example.front",
                    "is_visible": True,
                    "display_id": 0,
                    "type": 1,
                    "zord": 101,
                },
            ],
        }

        sc = unwrap_result(await ui.input_text(element_handle=_sample_handle(), text="42"))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "INPUT_FOCUS_TIMEOUT"
        assert sc["result"]["focus_dispatched"] is True
        assert sc["result"]["focus_verified"] is False
        assert sc["result"]["window_foreground"] is False
        assert sc["result"]["foreground_window_id"] == 2
        assert sc["result"]["dispatched"] is False
        mock_ui_operations.replace_focused_text.assert_not_called()

    async def test_sentinel_cleanup_requires_current_foreground_focus(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import ui

        initial = deepcopy(mock_ui_operations.find_element.return_value)
        sentinel = deepcopy(initial)
        sentinel["elements"][0]["text"] = "Agent中"
        sentinel["elements"][0]["focused"] = False
        responses = iter([initial, initial])

        def find_element(*args, **kwargs):
            return next(responses, sentinel)

        mock_ui_operations.find_element.side_effect = find_element

        sc = unwrap_result(await ui.input_text(element_handle=_sample_handle(), text="Agent"))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "TEXT_VERIFICATION_TIMEOUT"
        assert "cleanup was not dispatched" in sc["error"]["detail"]
        assert sc["result"]["cleanup_performed"] is False
        mock_ui_operations.press_key.assert_not_called()


class TestPressKey:
    async def test_press_home(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.press_key(key="Home"))

        assert sc["ok"] is True
        assert sc["result"]["message"] == "key event dispatched"
        assert sc["result"]["key"] == "KEYCODE_HOME"
        assert sc["result"]["key_code"] == 1
        assert sc["result"]["modifiers"] == []
        assert sc["result"]["event_key_codes"] == [1]
        assert sc["result"]["dispatched"] is True
        assert sc["result"]["effect_verified"] is False
        assert "action" not in sc["result"]
        mock_ui_operations.press_key.assert_called_once_with("device_001", 1)

    async def test_press_key_rejects_empty_key(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.press_key(key=""))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "INVALID_KEY"

    async def test_press_key_normalizes_common_aliases(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.press_key(key="volume_down"))

        assert sc["ok"] is True
        assert sc["result"]["key"] == "KEYCODE_VOLUME_DOWN"
        assert sc["result"]["key_code"] == 17
        assert sc["result"]["modifiers"] == []
        mock_ui_operations.press_key.assert_called_once_with("device_001", 17)

    async def test_press_key_normalizes_system_key_case_and_separators(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.press_key(key="dpad_up"))

        assert sc["ok"] is True
        assert sc["result"]["key"] == "KEYCODE_DPAD_UP"
        assert sc["result"]["key_code"] == 2012
        mock_ui_operations.press_key.assert_called_once_with("device_001", 2012)

    @pytest.mark.parametrize(
        ("key", "expected"),
        [
            ("Tab", 2049),
            ("KEYCODE_PAGE_UP", 2068),
            ("page-up", 2068),
            ("F24", 2827),
            ("button a", 2301),
            ("fingerprint_slide_down", 3234),
            ("Backspace", 2055),
            ("Delete", 2071),
        ],
    )
    async def test_press_key_accepts_complete_official_names_and_friendly_aliases(
        self,
        mock_hdc: MagicMock,
        mock_ui_operations: MagicMock,
        unwrap_result,
        key: str,
        expected: int,
    ):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.press_key(key=key))

        assert sc["ok"] is True
        assert sc["result"]["key_code"] == expected
        assert sc["result"]["key"].startswith("KEYCODE_")
        mock_ui_operations.press_key.assert_called_once_with("device_001", expected)

    async def test_press_key_supports_named_modifiers(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.press_key(key="V", modifiers=["Ctrl"]))

        assert sc["ok"] is True
        assert sc["result"]["key"] == "KEYCODE_V"
        assert sc["result"]["key_code"] == 2038
        assert sc["result"]["modifiers"] == ["Ctrl"]
        assert sc["result"]["event_key_codes"] == [2072, 2038]
        mock_ui_operations.send_key_event.assert_called_once_with("device_001", [2072, 2038])

    async def test_press_key_rejects_raw_shell_string(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.press_key(key="2072 2038"))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "INVALID_KEY"
        mock_ui_operations.send_key_event.assert_not_called()

    async def test_press_key_supports_meta_modifier(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.press_key(key="S", modifiers=["Meta"]))

        assert sc["ok"] is True
        assert sc["result"]["modifiers"] == ["Meta"]
        assert sc["result"]["event_key_codes"] == [2076, 2035]

    async def test_press_key_rejects_more_than_two_modifiers(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(
            await ui.press_key(key="S", modifiers=["Ctrl", "Alt", "Shift"])
        )

        assert sc["ok"] is False
        assert sc["error"]["code"] == "INVALID_MODIFIER_COUNT"

    async def test_press_key_rejects_unknown_numeric_keycode(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.press_key(key=65535))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "INVALID_KEY"
        assert sc["result"] == {
            "key": None,
            "key_code": None,
            "modifiers": [],
            "event_key_codes": [],
            "dispatched": False,
            "effect_verified": False,
        }

    async def test_press_key_rejects_duplicate_modifiers(
        self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result
    ):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.press_key(key="V", modifiers=["Ctrl", "Ctrl"]))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "DUPLICATE_MODIFIER"


class TestUiMutationLock:
    async def test_same_device_mutations_do_not_interleave(self):
        from harmonyos_dev_mcp.tools import ui

        first_entered = asyncio.Event()
        release_first = asyncio.Event()
        entered = []

        @ui._serialize_ui_mutation
        async def mutation(*, device_id: str, label: str):
            entered.append(label)
            if label == "first":
                first_entered.set()
                await release_first.wait()
            return label

        first = asyncio.create_task(mutation(device_id="device_001", label="first"))
        await first_entered.wait()
        second = asyncio.create_task(mutation(device_id="device_001", label="second"))
        await asyncio.sleep(0)

        assert entered == ["first"]
        release_first.set()
        assert await asyncio.gather(first, second) == ["first", "second"]

    async def test_different_devices_can_mutate_concurrently(self):
        from harmonyos_dev_mcp.tools import ui

        both_entered = asyncio.Event()
        entered = []

        @ui._serialize_ui_mutation
        async def mutation(*, device_id: str):
            entered.append(device_id)
            if len(entered) == 2:
                both_entered.set()
            await both_entered.wait()
            return device_id

        results = await asyncio.wait_for(
            asyncio.gather(
                mutation(device_id="device_001"),
                mutation(device_id="device_002"),
            ),
            timeout=1,
        )

        assert set(results) == {"device_001", "device_002"}


class TestFindElements:
    async def test_find_by_text(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.find_elements(text="登录"))

        assert sc["ok"] is True
        assert sc["result"]["count"] == 1
        mock_ui_operations.find_element.assert_called_once()

    async def test_find_by_type(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.find_elements(element_type="Button"))

        assert sc["ok"] is True
        assert sc["result"]["elements"][0]["lookup_is_broad"] is True
        mock_ui_operations.find_element.assert_called_once()

    async def test_find_includes_handle_metadata(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.find_elements(text="Button", bundle_name="com.example.app"))

        assert sc["ok"] is True
        element = sc["result"]["elements"][0]
        assert element["element_handle"]["compid"] == "comp_btn_login"
        assert element["element_handle"]["lookup_hint"]["text"] == "Button"
        assert element["lookup_is_broad"] is False
        assert "lookup_hint" not in element
        assert element["bounds"]["left"] == 80

    async def test_find_requires_criteria(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.find_elements())

        assert sc["ok"] is False
        assert sc["error"]["code"] == "MISSING_SEARCH_CRITERIA"

    async def test_find_returns_not_found_when_empty(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        mock_ui_operations.find_element.return_value = {"success": True, "elements": [], "count": 0}

        sc = unwrap_result(await ui.find_elements(text="missing"))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "ELEMENT_NOT_FOUND"
        assert sc["result"]["count"] == 0


class TestLongPressElement:
    async def test_long_press_by_handle(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.long_press(element_handle=_sample_handle()))

        assert sc["ok"] is True
        assert sc["result"]["resolved_via"] == "handle"
        assert sc["result"]["message"] == "long press dispatched"
        assert sc["result"]["dispatched"] is True
        assert sc["result"]["effect_verified"] is False
        mock_ui_operations.long_click.assert_called_once_with("device_001", 100, 200)

    async def test_long_press_by_element_id(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock, unwrap_result):
        from harmonyos_dev_mcp.tools import ui

        sc = unwrap_result(await ui.long_press(element_id="btn_login"))

        assert sc["ok"] is True
        assert sc["result"]["resolved_via"] == "search"


class TestScreenshot:
    async def test_screenshot_rejects_partial_bounds(self, mock_hdc: MagicMock, unwrap_result, monkeypatch):
        from harmonyos_dev_mcp.tools import ui

        monkeypatch.setattr(ui, "get_hdc", lambda: mock_hdc)
        sc = unwrap_result(await ui.screenshot(left=0, top=0, right=100))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "PARAM_CONFLICT"
