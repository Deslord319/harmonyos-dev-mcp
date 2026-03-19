from harmonyos_dev_mcp.utils.hdc.hdc_file import HdcFile


class _FakeHdcFile(HdcFile):
    def __init__(self, result):
        self._result = result

    def _execute_command(self, args, timeout=None):
        return dict(self._result)


class TestHdcFile:
    def test_get_realtime_logs_keeps_full_snapshot(self):
        device = _FakeHdcFile(
            {
                "success": True,
                "stdout": "line-1\nline-2\nline-3",
                "stderr": "",
                "returncode": 0,
            }
        )

        text = device.get_realtime_logs("device_001", lines=1)

        assert text == "line-1\nline-2\nline-3"

    def test_get_realtime_logs_filters_blank_lines(self):
        device = _FakeHdcFile(
            {
                "success": True,
                "stdout": "line-1\n\nline-2\n",
                "stderr": "",
                "returncode": 0,
            }
        )

        text = device.get_realtime_logs("device_001", lines=100)

        assert text == "line-1\nline-2"

    def test_get_realtime_logs_returns_empty_on_failure(self):
        device = _FakeHdcFile(
            {
                "success": False,
                "stdout": "",
                "stderr": "hilog failed",
                "returncode": 1,
            }
        )

        text = device.get_realtime_logs("device_001", lines=100)

        assert text == ""
