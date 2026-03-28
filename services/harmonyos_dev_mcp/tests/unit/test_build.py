"""Build tool tests with standardized MCP response envelope."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestBuildApp:
    @patch("harmonyos_dev_mcp.tools.build.HvigorWrapper")
    @pytest.mark.asyncio
    async def test_build_success(self, mock_hvigor_cls, unwrap_result):
        from harmonyos_dev_mcp.tools import build

        mock_hvigor = MagicMock()
        mock_hvigor.build.return_value = {
            "success": True,
            "output_path": "/path/to/output.hap",
        }
        mock_hvigor_cls.return_value = mock_hvigor

        sc = unwrap_result(await build.build_app(str(Path.cwd())))

        assert sc["ok"] is True
        assert sc["tool"] == "build_app"
        assert sc["result"]["output_path"] == "/path/to/output.hap"
        assert sc["result"]["target"] == "hap"
        assert "duration" in sc["result"]
        assert sc["result"]["errors"] == []
        assert sc["result"]["error_count"] == 0
        mock_hvigor.build.assert_called_once_with(
            target="hap",
            build_mode="debug",
            product="default",
            module_name=None,
        )

    @patch("harmonyos_dev_mcp.tools.build.HvigorWrapper")
    @pytest.mark.asyncio
    async def test_build_passes_product(self, mock_hvigor_cls, unwrap_result):
        from harmonyos_dev_mcp.tools import build

        mock_hvigor = MagicMock()
        mock_hvigor.build.return_value = {
            "success": True,
            "output_path": "/path/to/output.hap",
        }
        mock_hvigor_cls.return_value = mock_hvigor

        sc = unwrap_result(await build.build_app(str(Path.cwd()), product="qa"))

        assert sc["ok"] is True
        mock_hvigor.build.assert_called_once_with(
            target="hap",
            build_mode="debug",
            product="qa",
            module_name=None,
        )

    @patch("harmonyos_dev_mcp.tools.build.HvigorWrapper")
    @pytest.mark.asyncio
    async def test_build_failure(self, mock_hvigor_cls, unwrap_result):
        from harmonyos_dev_mcp.tools import build

        mock_hvigor = MagicMock()
        mock_hvigor.build.return_value = {"success": False, "stderr": "compiler exited with code 1"}
        mock_hvigor_cls.return_value = mock_hvigor

        sc = unwrap_result(await build.build_app(str(Path.cwd())))

        assert sc["ok"] is False
        assert sc["result"]["errors"] == []
        assert sc["result"]["error_count"] == 0
        assert sc["error"]["detail"] == "compiler exited with code 1"

    @patch("harmonyos_dev_mcp.tools.build.HvigorWrapper")
    @pytest.mark.asyncio
    async def test_build_timeout_error_includes_timeout_guidance(self, mock_hvigor_cls, unwrap_result):
        from harmonyos_dev_mcp.tools import build

        mock_hvigor = MagicMock()
        mock_hvigor.build.return_value = {
            "success": False,
            "error_code": "BUILD_TIMEOUT",
            "stderr": "build timed out after 600s",
        }
        mock_hvigor_cls.return_value = mock_hvigor

        sc = unwrap_result(await build.build_app(str(Path.cwd())))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "BUILD_TIMEOUT"
        assert "at least 60 seconds" in sc["error"]["detail"]
        assert "120 seconds is recommended" in sc["error"]["detail"]

    @patch("harmonyos_dev_mcp.tools.build.HvigorWrapper")
    @pytest.mark.asyncio
    async def test_build_accepts_release_mode(self, mock_hvigor_cls, unwrap_result):
        from harmonyos_dev_mcp.tools import build

        mock_hvigor = MagicMock()
        mock_hvigor.build.return_value = {
            "success": True,
            "output_path": "/path/to/output.hap",
        }
        mock_hvigor_cls.return_value = mock_hvigor

        sc = unwrap_result(await build.build_app(str(Path.cwd()), build_mode="release"))

        assert sc["ok"] is True
        mock_hvigor.build.assert_called_once_with(
            target="hap",
            build_mode="release",
            product="default",
            module_name=None,
        )

    @patch("harmonyos_dev_mcp.tools.build.HvigorWrapper")
    @pytest.mark.asyncio
    async def test_build_failure_uses_current_process_output_only(self, mock_hvigor_cls, unwrap_result):
        from harmonyos_dev_mcp.tools import build

        mock_hvigor = MagicMock()
        mock_hvigor.build.return_value = {
            "success": False,
            "stderr": (
                "1 ERROR: 10505001 ArkTS Compiler Error\n"
                "Error Message: ';' expected. At File: "
                "/path/to/SnakeGameBoard.ets:116:20\n"
                "> hvigor ERROR: BUILD FAILED in 2 s 582 ms\n"
            ),
        }
        mock_hvigor_cls.return_value = mock_hvigor

        sc = unwrap_result(await build.build_app(str(Path.cwd())))

        assert sc["ok"] is False
        assert "Error Message: ';' expected." in sc["error"]["detail"]
        assert "> hvigor ERROR: BUILD FAILED in 2 s 582 ms" in sc["error"]["detail"]

    @patch("harmonyos_dev_mcp.tools.build.HvigorWrapper")
    @pytest.mark.asyncio
    async def test_build_extracts_file_colon_error_format(self, mock_hvigor_cls, unwrap_result):
        from harmonyos_dev_mcp.tools import build

        mock_hvigor = MagicMock()
        mock_hvigor.build.return_value = {
            "success": False,
            "stderr": "entry/src/main/ets/pages/Index.ets:23:17 - error Type mismatch",
        }
        mock_hvigor_cls.return_value = mock_hvigor

        sc = unwrap_result(await build.build_app(str(Path.cwd())))

        assert sc["ok"] is False
        assert sc["result"]["error_count"] == 1
        assert sc["result"]["errors"][0]["file"] == "entry/src/main/ets/pages/Index.ets"
        assert sc["result"]["errors"][0]["line"] == 23
        assert sc["result"]["errors"][0]["column"] == 17

    @patch("harmonyos_dev_mcp.tools.build.HvigorWrapper")
    @pytest.mark.asyncio
    async def test_build_extracts_error_file_line_column_format(self, mock_hvigor_cls, unwrap_result):
        from harmonyos_dev_mcp.tools import build

        mock_hvigor = MagicMock()
        mock_hvigor.build.return_value = {
            "success": False,
            "stderr": "ERROR File: /tmp/build-profile.json5 line: 12 column: 3 - invalid trailing comma",
        }
        mock_hvigor_cls.return_value = mock_hvigor

        sc = unwrap_result(await build.build_app(str(Path.cwd())))

        assert sc["ok"] is False
        assert sc["result"]["error_count"] == 1
        assert sc["result"]["errors"][0]["file"] == "build-profile.json5"
        assert sc["result"]["errors"][0]["line"] == 12
        assert sc["result"]["errors"][0]["column"] == 3

    @patch("harmonyos_dev_mcp.tools.build.HvigorWrapper")
    @pytest.mark.asyncio
    async def test_build_har_requires_module_name(self, mock_hvigor_cls, unwrap_result):
        from harmonyos_dev_mcp.tools import build

        sc = unwrap_result(await build.build_app(str(Path.cwd()), target="har"))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "MISSING_MODULE_NAME"

    @patch("harmonyos_dev_mcp.tools.build.HvigorWrapper")
    @pytest.mark.asyncio
    async def test_build_with_invalid_target(self, mock_hvigor_cls, unwrap_result):
        from harmonyos_dev_mcp.tools import build

        sc = unwrap_result(await build.build_app(str(Path.cwd()), target="zip"))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "INVALID_BUILD_TARGET"

    @patch("harmonyos_dev_mcp.tools.build.HvigorWrapper")
    @pytest.mark.asyncio
    async def test_build_rejects_invalid_project_path(self, mock_hvigor_cls, unwrap_result):
        from harmonyos_dev_mcp.tools import build

        sc = unwrap_result(await build.build_app("Z:/path/that/does/not/exist"))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "INVALID_PROJECT_PATH"
        mock_hvigor_cls.assert_not_called()

    @patch("harmonyos_dev_mcp.tools.build.HvigorWrapper")
    @pytest.mark.asyncio
    async def test_build_rejects_invalid_build_mode(self, mock_hvigor_cls, unwrap_result):
        from harmonyos_dev_mcp.tools import build

        sc = unwrap_result(await build.build_app(str(Path.cwd()), build_mode="profile"))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "INVALID_BUILD_MODE"
        mock_hvigor_cls.assert_not_called()


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
        from harmonyos_dev_mcp.tools.device_support import DeviceToolSupport

        monkeypatch.setattr(
            DeviceToolSupport,
            "get_device_id",
            staticmethod(
                lambda device_id=None: (
                    False,
                    None,
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

    @pytest.mark.asyncio
    async def test_install_requires_package_path(self, mock_hdc: MagicMock, unwrap_result, monkeypatch):
        from harmonyos_dev_mcp.tools import build

        monkeypatch.setattr(build, "get_hdc", lambda: mock_hdc)
        sc = unwrap_result(await build.install_app("", device_id="device_001"))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "MISSING_HAP_PATH"

    @pytest.mark.asyncio
    async def test_install_rejects_invalid_package_suffix(self, mock_hdc: MagicMock, unwrap_result, monkeypatch):
        from harmonyos_dev_mcp.tools import build

        monkeypatch.setattr(build, "get_hdc", lambda: mock_hdc)
        sc = unwrap_result(await build.install_app("/path/to/app.zip", device_id="device_001"))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "INVALID_APP_PACKAGE"


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
    async def test_run_fails_when_ability_detection_fails(self, mock_hdc: MagicMock, unwrap_result, monkeypatch):
        from harmonyos_dev_mcp.tools import build

        monkeypatch.setattr(build, "get_hdc", lambda: mock_hdc)
        mock_hdc.get_main_ability.return_value = {"success": False, "error": "Package not found"}
        mock_hdc.get_package_info.return_value = {"success": False, "error": "Package not found"}

        sc = unwrap_result(await build.run_app("com.example.app"))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "ABILITY_RESOLUTION_FAILED"
        assert sc["result"]["ability_name"] == ""
        assert sc["result"]["command_success"] is False

    @pytest.mark.asyncio
    async def test_run_fails_when_no_device(self, no_device_mock: MagicMock, unwrap_result, monkeypatch):
        from harmonyos_dev_mcp.tools import build
        from harmonyos_dev_mcp.tools.device_support import DeviceToolSupport

        monkeypatch.setattr(build, "get_hdc", lambda: no_device_mock)
        monkeypatch.setattr(
            DeviceToolSupport,
            "get_device_id",
            staticmethod(
                lambda device_id=None: (
                    False,
                    None,
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

    @pytest.mark.asyncio
    async def test_uninstall_requires_bundle_name(self, mock_hdc: MagicMock, unwrap_result, monkeypatch):
        from harmonyos_dev_mcp.tools import build

        monkeypatch.setattr(build, "get_hdc", lambda: mock_hdc)
        sc = unwrap_result(await build.uninstall_app("", device_id="device_001"))

        assert sc["ok"] is False
        assert sc["error"]["code"] == "MISSING_BUNDLE_NAME"
