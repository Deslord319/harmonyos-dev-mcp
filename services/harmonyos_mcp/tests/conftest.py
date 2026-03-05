"""Pytest fixtures for harmonyos_mcp tests."""

import sys
from typing import Generator
from unittest.mock import MagicMock

import pytest
from loguru import logger


def pytest_configure(config):
    logger.remove()
    logger.add(
        sys.stderr,
        format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level="WARNING",
        colorize=True,
    )


@pytest.fixture(autouse=True)
def reset_container():
    yield
    from harmonyos_mcp.container import container

    container.reset()
    import harmonyos_mcp.container as container_mod

    container_mod._registered = False


@pytest.fixture
def mock_hdc() -> Generator[MagicMock, None, None]:
    from harmonyos_mcp.utils.hdc import HdcWrapper
    from harmonyos_mcp.container import container
    import harmonyos_mcp.container as container_mod

    mock = MagicMock(spec=HdcWrapper)

    mock.list_devices.return_value = ["device_001", "device_002"]
    mock.list_devices_with_info.return_value = [
        {
            "device_id": "device_001",
            "device_name": "HUAWEI Mate 60",
            "os_version": "HarmonyOS 4.2",
            "status": "online",
        },
        {
            "device_id": "device_002",
            "device_name": "HUAWEI MatePad",
            "os_version": "HarmonyOS 4.0",
            "status": "online",
        },
    ]
    mock.install_app.return_value = True
    mock.uninstall_app.return_value = True
    mock.get_main_ability.return_value = {
        "success": True,
        "candidates": [{"ability_name": "MainAbility", "module_name": "entry", "type": "page"}],
        "recommended": 0,
    }
    mock.start_app.return_value = {
        "success": True,
        "command_success": True,
        "window_found": True,
    }
    mock.list_packages.return_value = {
        "success": True,
        "packages": ["com.example.app1", "com.example.app2"],
        "count": 2,
    }
    mock.get_package_info.return_value = {
        "success": True,
        "abilities": [{"name": "MainAbility", "module": "entry", "type": "page"}],
        "modules": ["entry"],
        "main_ability": {"name": "MainAbility", "module": "entry", "type": "page"},
    }
    mock.get_window_list.return_value = {
        "success": True,
        "windows": [{"window_id": 1, "bundle_name": "com.example.app", "is_visible": True}],
    }
    mock.get_ui_tree_raw.return_value = {"success": True, "ui_tree": {"type": "Root", "children": []}}
    mock.get_realtime_logs.return_value = "01-31 10:00:00.123  1234  1234 I MyTag: Test log"
    mock.get_app_pid.return_value = 1234

    container.register(HdcWrapper, lambda: mock)
    container_mod._registered = True

    yield mock


@pytest.fixture
def single_device_mock(mock_hdc: MagicMock) -> MagicMock:
    mock_hdc.list_devices.return_value = ["device_001"]
    mock_hdc.list_devices_with_info.return_value = [
        {
            "device_id": "device_001",
            "device_name": "HUAWEI Mate 60",
            "os_version": "HarmonyOS 4.2",
            "status": "online",
        }
    ]
    return mock_hdc


@pytest.fixture
def no_device_mock(mock_hdc: MagicMock) -> MagicMock:
    mock_hdc.list_devices.return_value = []
    mock_hdc.list_devices_with_info.return_value = []
    return mock_hdc


@pytest.fixture
def mock_ui_operations() -> Generator[MagicMock, None, None]:
    from harmonyos_mcp.utils.wrappers.ui_operations import UiTestWrapper
    from harmonyos_mcp.container import container
    import harmonyos_mcp.container as container_mod

    mock = MagicMock(spec=UiTestWrapper)

    mock.click.return_value = {"success": True, "x": 100, "y": 200}
    mock.double_click.return_value = {"success": True, "x": 100, "y": 200}
    mock.long_click.return_value = {"success": True, "x": 100, "y": 200}
    mock.swipe.return_value = {"success": True, "from_x": 1, "from_y": 2, "to_x": 3, "to_y": 4}
    mock.swipe_direction.return_value = {
        "success": True,
        "from_x": 1,
        "from_y": 2,
        "to_x": 3,
        "to_y": 4,
        "direction": "up",
    }
    mock.input_text.return_value = {"success": True, "text": "ok", "x": 100, "y": 200}
    mock.press_key.return_value = {"success": True, "key": "Home"}
    mock.find_element.return_value = {
        "success": True,
        "elements": [{"x": 100, "y": 200, "text": "Button", "type": "Button"}],
        "count": 1,
    }

    container.register(UiTestWrapper, lambda: mock)
    container_mod._registered = True

    yield mock


@pytest.fixture
def unwrap_result():
    def _unwrap(result: dict) -> dict:
        assert "content" in result
        assert "structuredContent" in result
        assert "isError" in result
        sc = result["structuredContent"]
        assert result["isError"] is (not sc["ok"])
        assert sc["meta"]["request_id"]
        assert sc["meta"]["duration_ms"] >= 0
        return sc

    return _unwrap
