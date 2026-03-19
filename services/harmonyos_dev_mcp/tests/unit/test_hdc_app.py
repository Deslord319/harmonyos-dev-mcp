from unittest.mock import MagicMock


class TestHdcAppPidBundleCache:
    def test_get_bundle_name_by_pid_uses_cache_and_refreshes_ttl(self, monkeypatch):
        from harmonyos_dev_mcp.utils.hdc.hdc_app import HdcApp

        app = HdcApp()
        app.execute_shell = MagicMock(return_value={"success": True, "stdout": "com.example.settings\x00", "stderr": ""})

        times = iter([100.0, 100.0, 101.0, 101.0])
        monkeypatch.setattr("harmonyos_dev_mcp.utils.hdc.hdc_app.time.monotonic", lambda: next(times))

        first = app.get_bundle_name_by_pid("device_001", 123)
        second = app.get_bundle_name_by_pid("device_001", 123)

        assert first == "com.example.settings"
        assert second == "com.example.settings"
        app.execute_shell.assert_called_once_with("device_001", "cat /proc/123/cmdline")
        expires_at, cached_bundle = app._pid_bundle_cache[("device_001", 123)]
        assert cached_bundle == "com.example.settings"
        assert expires_at == 104.0

    def test_get_bundle_name_by_pid_requeries_after_expiration(self, monkeypatch):
        from harmonyos_dev_mcp.utils.hdc.hdc_app import HdcApp

        app = HdcApp()
        app.execute_shell = MagicMock(return_value={"success": True, "stdout": "com.example.settings\x00", "stderr": ""})

        times = iter([100.0, 100.0, 104.2, 104.2, 104.2, 104.2])
        monkeypatch.setattr("harmonyos_dev_mcp.utils.hdc.hdc_app.time.monotonic", lambda: next(times))

        first = app.get_bundle_name_by_pid("device_001", 123)
        second = app.get_bundle_name_by_pid("device_001", 123)

        assert first == "com.example.settings"
        assert second == "com.example.settings"
        assert app.execute_shell.call_count == 2

    def test_get_bundle_name_by_pid_caches_none_results(self, monkeypatch):
        from harmonyos_dev_mcp.utils.hdc.hdc_app import HdcApp

        app = HdcApp()
        app.execute_shell = MagicMock(side_effect=[
            {"success": False, "stdout": "", "stderr": "no proc"},
            {"success": False, "stdout": "", "stderr": "no ps"},
        ])

        times = iter([100.0, 100.0, 101.0, 101.0])
        monkeypatch.setattr("harmonyos_dev_mcp.utils.hdc.hdc_app.time.monotonic", lambda: next(times))

        first = app.get_bundle_name_by_pid("device_001", 999)
        second = app.get_bundle_name_by_pid("device_001", 999)

        assert first is None
        assert second is None
        assert app.execute_shell.call_count == 2
