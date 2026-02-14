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
    """logs_query 测试（raw_files 模式）"""

    @pytest.mark.asyncio
    async def test_uses_first_device_when_not_specified(self, mock_hdc: MagicMock):
        """未指定设备时使用第一个设备"""
        from harmonyos_mcp.tools import logs

        result = await logs.logs_query(raw_files=True)

        assert result['device_id'] == 'device_001'
        mock_hdc.hilog_receive.assert_called_once_with('device_001', None)

    @pytest.mark.asyncio
    async def test_uses_specified_device(self, mock_hdc: MagicMock):
        """使用指定的设备"""
        from harmonyos_mcp.tools import logs

        result = await logs.logs_query(device_id='device_002', raw_files=True)

        assert result['device_id'] == 'device_002'
        mock_hdc.hilog_receive.assert_called_once_with('device_002', None)

    @pytest.mark.asyncio
    async def test_uses_specified_save_path(self, mock_hdc: MagicMock):
        """使用指定的保存路径"""
        from harmonyos_mcp.tools import logs

        result = await logs.logs_query(raw_files=True, save_path='/tmp/logs')

        mock_hdc.hilog_receive.assert_called_once_with('device_001', '/tmp/logs')

    @pytest.mark.asyncio
    async def test_fails_when_no_device(self, no_device_mock: MagicMock):
        """无设备时返回错误"""
        from harmonyos_mcp.tools import logs

        result = await logs.logs_query(raw_files=True)

        assert result['success'] is False
        assert '没有找到' in result['error']
