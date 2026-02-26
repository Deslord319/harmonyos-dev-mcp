"""
设备管理与日志收集工具单元测试
"""
import pytest
from unittest.mock import MagicMock


class TestListDevices:
    """list_devices 测试"""

    @pytest.mark.asyncio
    async def test_returns_device_list(self, mock_hdc: MagicMock):
        """应返回设备列表"""
        from harmonyos_mcp.tools import general

        result = await general.list_devices()

        assert result['success'] is True
        assert result['count'] == 2
        assert 'device_001' in result['devices']
        assert 'device_002' in result['devices']
        mock_hdc.list_devices.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_empty_devices(self, no_device_mock: MagicMock):
        """无设备时应返回空列表"""
        from harmonyos_mcp.tools import general

        result = await general.list_devices()

        assert result['success'] is True
        assert result['count'] == 0
        assert result['devices'] == []

    @pytest.mark.asyncio
    async def test_handles_exception(self, mock_hdc: MagicMock):
        """异常时应返回错误"""
        from harmonyos_mcp.tools import general

        mock_hdc.list_devices.side_effect = Exception("Connection failed")

        result = await general.list_devices()

        assert result['success'] is False
        assert 'Connection failed' in result['error']


class TestLogsQuery:
    """logs_query 测试"""

    @pytest.mark.asyncio
    async def test_direct_logs_input(self, mock_hdc: MagicMock):
        """直接传入日志行列表"""
        from harmonyos_mcp.tools import logs

        test_logs = [
            "01-31 10:00:00.123  1000  2000 E MyApp: test error",
            "01-31 10:00:01.456  1000  2000 I MyApp: test info",
        ]
        result = await logs.logs_query(logs=test_logs)

        assert result['success'] is True
        assert result['source'] == 'direct'
        assert result['total_lines'] == 2

    @pytest.mark.asyncio
    async def test_level_filter(self, mock_hdc: MagicMock):
        """日志级别过滤"""
        from harmonyos_mcp.tools import logs

        test_logs = [
            "01-31 10:00:00.123  1000  2000 E MyApp: error",
            "01-31 10:00:01.456  1000  2000 I MyApp: info",
            "01-31 10:00:02.789  1000  2000 W MyApp: warning",
        ]
        result = await logs.logs_query(logs=test_logs, level='E')

        assert result['success'] is True
        assert result['total_lines'] == 1

    @pytest.mark.asyncio
    async def test_fails_when_no_device(self, no_device_mock: MagicMock):
        """无设备时返回错误"""
        from harmonyos_mcp.tools import logs

        result = await logs.logs_query()

        assert result['success'] is False
        assert '没有找到' in result['error']
