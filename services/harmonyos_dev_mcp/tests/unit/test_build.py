"""Build tool tests with standardized MCP response envelope."""

from unittest.mock import MagicMock, patch

import pytest


class TestBuildApp:
    @patch("harmonyos_mcp.tools.build.HvigorWrapper")
    @pytest.mark.asyncio
    async def test_build_success(self, mock_hvigor_cls, unwrap_result):
        from harmonyos_dev_mcp.tools import build

        mock_hvigor = MagicMock()
        mock_hvigor.build_hap.return_value = {
            "success": True,
            "hap_path": "/path/to/output.hap",
        }
        mock_hvigor_cls.return_value = mock_hvigor

        sc = unwrap_result(await build.build_app("/path/to/project"))

        assert sc["ok"] is True
        assert sc["tool"] == "build_app"
        assert sc["result"]["hap_path"] == "/path/to/output.hap"
        assert "duration" in sc["result"]
        assert "long-running task" in sc["result"]["hint"]
        assert sc["result"]["errors"] == []
        assert sc["result"]["error_count"] == 0

    @patch("harmonyos_mcp.tools.build.HvigorWrapper")
    @pytest.mark.asyncio
    async def test_build_failure(self, mock_hvigor_cls, unwrap_result):
        from harmonyos_dev_mcp.tools import build

        mock_hvigor = MagicMock()
        mock_hvigor.build_hap.return_value = {"success": False, "stderr": "compiler exited with code 1"}
        mock_hvigor_cls.return_value = mock_hvigor

        sc = unwrap_result(await build.build_app("/path/to/project"))

        assert sc["ok"] is False
        assert "long-running task" in sc["result"]["hint"]
        assert sc["result"]["errors"] == []
        assert sc["result"]["error_count"] == 0
        assert sc["error"]["detail"] == "compiler exited with code 1"

    @patch("harmonyos_mcp.tools.build.HvigorWrapper")
    @pytest.mark.asyncio
    async def test_build_with_release_mode(self, mock_hvigor_cls):
        from harmonyos_dev_mcp.tools import build

        mock_hvigor = MagicMock()
        mock_hvigor.build_hap.return_value = {"success": True}
        mock_hvigor_cls.return_value = mock_hvigor

        await build.build_app("/path/to/project", build_mode="release")
        mock_hvigor.build_hap.assert_called_once_with(build_mode="release")

    @patch("harmonyos_mcp.tools.build.HvigorWrapper")
    @pytest.mark.asyncio
    async def test_build_failure_uses_current_process_output_only(self, mock_hvigor_cls, unwrap_result):
        from harmonyos_dev_mcp.tools import build

        mock_hvigor = MagicMock()
        mock_hvigor.build_hap.return_value = {
            "success": False,
            "stderr": (
                "1 ERROR: 10505001 ArkTS Compiler Error\n"
                "Error Message: ';' expected. At File: "
                "/path/to/SnakeGameBoard.ets:116:20\n"
                "> hvigor ERROR: BUILD FAILED in 2 s 582 ms\n"
            ),
        }
        mock_hvigor_cls.return_value = mock_hvigor

        sc = unwrap_result(await build.build_app("/path/to/project"))

        assert sc["ok"] is False
        assert "Error Message: ';' expected." in sc["error"]["detail"]
        assert "> hvigor ERROR: BUILD FAILED in 2 s 582 ms" in sc["error"]["detail"]


class TestInstallApp:
    @pytest.mark.asyncio
    async def test_install_success(self, mock_hdc: MagicMock, unwrap_result, monkeypatch):
        from harmonyos_dev_mcp.tools import build

        monkeypatch.setattr(build, "get_hdc", lambda: mock_hdc)
        sc = unwrap_result(await build.install_app("/path/to/app.hap", device_id="device_001"))

        assert sc["ok"] is True
        assert sc["tool"] == "install_app"
        assert sc["result"]["device_id"]
        assert sc["result"]["hap_path"] == "/path/to/app.hap"

    @pytest.mark.asyncio
    async def test_install_to_specific_device(self, mock_hdc: MagicMock, unwrap_result, monkeypatch):
        from harmonyos_dev_mcp.tools import build

        monkeypatch.setattr(build, "get_hdc", lambda: mock_hdc)
        sc = unwrap_result(await build.install_app("/path/to/app.hap", device_id="device_002"))

        assert sc["result"]["device_id"] == "device_002"
        mock_hdc.install_app.assert_called_with("device_002", "/path/to/app.hap")

    @pytest.mark.asyncio
    async def test_install_fails_when_no_device(self, no_device_mock: MagicMock, unwrap_result, monkeypatch):
        from harmonyos_dev_mcp.tools import build
        from harmonyos_dev_mcp.tools.device_base import ToolBase

        monkeypatch.setattr(
            ToolBase,
            "get_device_id",
            staticmethod(
                lambda device_id=None: (
                    False,
                    {
                        "tool": "with_device",
                        "ok": False,
                        "result": {},
                        "error": {"code": "DEVICE_NOT_FOUND", "detail": "No device found"},
                        "meta": {},
                    },
                )
            ),
        )
        sc = unwrap_result(await build.install_app("/path/to/app.hap"))

        assert sc["ok"] is False
        assert sc["error"]["detail"]

    @pytest.mark.asyncio
    async def test_install_detects_business_failure_even_when_command_returns_success(
        self, mock_hdc: MagicMock, unwrap_result, monkeypatch
    ):
        from harmonyos_dev_mcp.tools import build

        monkeypatch.setattr(build, "get_hdc", lambda: mock_hdc)
        mock_hdc.install_app.return_value = {
            "success": False,
            "stdout": "[INSTALL_FAILED] install bundle failed, code:9568320",
            "stderr": "",
            "returncode": 0,
            "error": "[INSTALL_FAILED] install bundle failed, code:9568320",
            "error_code": "INSTALL_FAILED",
        }

        sc = unwrap_result(await build.install_app("/path/to/app.hap", device_id="device_001"))

        assert sc["ok"] is False
        assert sc["error"]["detail"] == "[INSTALL_FAILED] install bundle failed, code:9568320"
        assert sc["result"]["hap_path"] == "/path/to/app.hap"


class TestRunApp:
    @pytest.mark.asyncio
    async def test_auto_detect_ability(self, mock_hdc: MagicMock, unwrap_result, monkeypatch):
        from harmonyos_dev_mcp.tools import build

        monkeypatch.setattr(build, "get_hdc", lambda: mock_hdc)
        sc = unwrap_result(await build.run_app("com.example.app"))

        assert sc["ok"] is True
        assert sc["result"]["ability_name"] == "MainAbility"
        assert sc["result"]["module_name"] == "entry"
        assert sc["result"]["auto_detected"] is True

    @pytest.mark.asyncio
    async def test_use_specified_ability(self, mock_hdc: MagicMock, unwrap_result, monkeypatch):
        from harmonyos_dev_mcp.tools import build

        monkeypatch.setattr(build, "get_hdc", lambda: mock_hdc)
        sc = unwrap_result(
            await build.run_app("com.example.app", ability_name="CustomAbility", module_name="feature")
        )

        assert sc["result"]["ability_name"] == "CustomAbility"
        assert sc["result"]["module_name"] == "feature"
        assert sc["result"]["auto_detected"] is False

    @pytest.mark.asyncio
    async def test_use_default_ability_when_detection_fails(self, mock_hdc: MagicMock, unwrap_result, monkeypatch):
        from harmonyos_dev_mcp.tools import build

        monkeypatch.setattr(build, "get_hdc", lambda: mock_hdc)
        mock_hdc.get_main_ability.return_value = {"success": False, "error": "Package not found"}

        sc = unwrap_result(await build.run_app("com.example.app"))

        assert sc["result"]["ability_name"] == "MainAbility"
        assert sc["result"]["module_name"] == "entry"
        assert sc["result"]["auto_detected"] is True

    @pytest.mark.asyncio
    async def test_run_fails_when_no_device(self, no_device_mock: MagicMock, unwrap_result, monkeypatch):
        from harmonyos_dev_mcp.tools import build
        from harmonyos_dev_mcp.tools.device_base import ToolBase

        monkeypatch.setattr(build, "get_hdc", lambda: no_device_mock)
        monkeypatch.setattr(
            ToolBase,
            "get_device_id",
            staticmethod(
                lambda device_id=None: (
                    False,
                    {
                        "tool": "with_device",
                        "ok": False,
                        "result": {},
                        "error": {"code": "DEVICE_NOT_FOUND", "detail": "No device found"},
                        "meta": {},
                    },
                )
            ),
        )
        sc = unwrap_result(await build.run_app("com.example.app"))
        assert sc["ok"] is False

    @pytest.mark.asyncio
    async def test_run_command_success_but_window_unverified_has_neutral_detail(
        self, mock_hdc: MagicMock, unwrap_result, monkeypatch
    ):
        from harmonyos_dev_mcp.tools import build

        monkeypatch.setattr(build, "get_hdc", lambda: mock_hdc)
        mock_hdc.start_app.return_value = {
            "success": False,
            "error": "应用窗口未出现（可能ability_name或module_name错误）",
            "command_success": True,
            "window_found": False,
        }

        sc = unwrap_result(await build.run_app("com.example.app"))

        assert sc["ok"] is False
        assert sc["result"]["command_success"] is True
        assert sc["result"]["window_found"] is False
        assert sc["error"]["detail"] == "app launch command succeeded, but window verification did not pass"


class TestUninstallApp:
    @pytest.mark.asyncio
    async def test_uninstall_success(self, mock_hdc: MagicMock, unwrap_result, monkeypatch):
        from harmonyos_dev_mcp.tools import build

        monkeypatch.setattr(build, "get_hdc", lambda: mock_hdc)
        sc = unwrap_result(await build.uninstall_app("com.example.app", device_id="device_001"))

        assert sc["ok"] is True
        assert sc["result"]["bundle_name"] == "com.example.app"
        mock_hdc.uninstall_app.assert_called_once()

    @pytest.mark.asyncio
    async def test_uninstall_from_specific_device(self, mock_hdc: MagicMock, unwrap_result, monkeypatch):
        from harmonyos_dev_mcp.tools import build

        monkeypatch.setattr(build, "get_hdc", lambda: mock_hdc)
        await build.uninstall_app("com.example.app", device_id="device_002")
        mock_hdc.uninstall_app.assert_called_with("device_002", "com.example.app")

    @pytest.mark.asyncio
    async def test_uninstall_detects_business_failure_even_when_command_returns_success(
        self, mock_hdc: MagicMock, unwrap_result, monkeypatch
    ):
        from harmonyos_dev_mcp.tools import build

        monkeypatch.setattr(build, "get_hdc", lambda: mock_hdc)
        mock_hdc.uninstall_app.return_value = {
            "success": False,
            "stdout": "uninstall failed: bundle is not installed",
            "stderr": "",
            "returncode": 0,
            "error": "uninstall failed: bundle is not installed",
            "error_code": "UNINSTALL_FAILED",
        }

        sc = unwrap_result(await build.uninstall_app("com.example.app", device_id="device_001"))

        assert sc["ok"] is False
        assert sc["error"]["detail"] == "uninstall failed: bundle is not installed"
        assert sc["result"]["bundle_name"] == "com.example.app"
