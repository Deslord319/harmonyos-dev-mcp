from harmonyos_mcp.utils.hdc.hdc_device import HdcDevice


class _FakeHdcDevice(HdcDevice):
    def __init__(self, result):
        self._result = result

    def _execute_command(self, args, timeout=None):
        return dict(self._result)


class TestHdcDevice:
    def test_install_marks_explicit_failure_output_as_failed(self):
        device = _FakeHdcDevice(
            {
                "success": True,
                "stdout": "[INSTALL_FAILED] install bundle failed, code:9568320",
                "stderr": "",
                "returncode": 0,
            }
        )

        result = device.install_app("device_001", "/path/to/app.hap")

        assert result["success"] is False
        assert result["error_code"] == "INSTALL_FAILED"
        assert result["error"] == "[INSTALL_FAILED] install bundle failed, code:9568320"

    def test_install_marks_failed_to_install_variant_as_failed(self):
        device = _FakeHdcDevice(
            {
                "success": True,
                "stdout": "Failed to install package because signature verification failed",
                "stderr": "",
                "returncode": 0,
            }
        )

        result = device.install_app("device_001", "/path/to/app.hap")

        assert result["success"] is False
        assert result["error_code"] == "INSTALL_FAILED"

    def test_install_does_not_fail_on_non_failure_code_text(self):
        device = _FakeHdcDevice(
            {
                "success": True,
                "stdout": "install bundle successfully, versionCode: 12345",
                "stderr": "",
                "returncode": 0,
            }
        )

        result = device.install_app("device_001", "/path/to/app.hap")

        assert result["success"] is True
        assert "error_code" not in result

    def test_uninstall_marks_explicit_failure_output_as_failed(self):
        device = _FakeHdcDevice(
            {
                "success": True,
                "stdout": "uninstall failed: bundle is not installed",
                "stderr": "",
                "returncode": 0,
            }
        )

        result = device.uninstall_app("device_001", "com.example.app")

        assert result["success"] is False
        assert result["error_code"] == "UNINSTALL_FAILED"
        assert result["error"] == "uninstall failed: bundle is not installed"

    def test_uninstall_marks_failed_to_uninstall_variant_as_failed(self):
        device = _FakeHdcDevice(
            {
                "success": True,
                "stdout": "FAILED TO UNINSTALL bundle because it is protected",
                "stderr": "",
                "returncode": 0,
            }
        )

        result = device.uninstall_app("device_001", "com.example.app")

        assert result["success"] is False
        assert result["error_code"] == "UNINSTALL_FAILED"

    def test_uninstall_does_not_fail_on_non_failure_error_label(self):
        device = _FakeHdcDevice(
            {
                "success": True,
                "stdout": "uninstall finished, error code field retained for audit: 0",
                "stderr": "",
                "returncode": 0,
            }
        )

        result = device.uninstall_app("device_001", "com.example.app")

        assert result["success"] is True
        assert "error_code" not in result
