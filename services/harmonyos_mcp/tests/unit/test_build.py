"""
构建部署工具单元测试
"""

import pytest
from unittest.mock import MagicMock, patch


class TestBuildApp:
    """build_app 测试"""

    @patch('harmonyos_mcp.tools.build.HvigorWrapper')
    @pytest.mark.asyncio
    async def test_build_success(self, mock_hvigor_cls):
        """构建成功"""
        from harmonyos_mcp.tools import build

        mock_hvigor = MagicMock()
        mock_hvigor.build_hap.return_value = {
            'success': True,
            'hap_path': '/path/to/output.hap'
        }
        mock_hvigor_cls.return_value = mock_hvigor

        result = await build.build_app('/path/to/project')

        assert result['success'] is True
        assert result['hap_path'] == '/path/to/output.hap'
        assert '成功' in result['message']
        assert 'duration' in result
        assert result['errors'] == []
        assert result['error_count'] == 0

    @patch('harmonyos_mcp.tools.build.HvigorWrapper')
    @pytest.mark.asyncio
    async def test_build_failure(self, mock_hvigor_cls):
        """构建失败"""
        from harmonyos_mcp.tools import build

        mock_hvigor = MagicMock()
        mock_hvigor.build_hap.return_value = {'success': False, 'stderr': 'compiler exited with code 1'}
        mock_hvigor_cls.return_value = mock_hvigor

        result = await build.build_app('/path/to/project')

        assert result['success'] is False
        assert '失败' in result['message']
        assert result['errors'] == []
        assert result['error_count'] == 0
        assert result['error'] == 'compiler exited with code 1'

    @patch('harmonyos_mcp.tools.build.HvigorWrapper')
    @pytest.mark.asyncio
    async def test_build_with_release_mode(self, mock_hvigor_cls):
        """使用 release 模式构建"""
        from harmonyos_mcp.tools import build

        mock_hvigor = MagicMock()
        mock_hvigor.build_hap.return_value = {'success': True}
        mock_hvigor_cls.return_value = mock_hvigor

        await build.build_app('/path/to/project', build_mode='release')

        mock_hvigor.build_hap.assert_called_once_with(build_mode='release')

    @patch('harmonyos_mcp.tools.build.HvigorWrapper')
    @pytest.mark.asyncio
    async def test_build_failure_uses_current_process_output_only(self, mock_hvigor_cls):
        """失败时仅解析本次 hvigor 进程输出"""
        from harmonyos_mcp.tools import build

        mock_hvigor = MagicMock()
        mock_hvigor.build_hap.return_value = {
            'success': False,
            'stderr': (
                "1 ERROR: 10505001 ArkTS Compiler Error\n"
                "Error Message: ';' expected. At File: "
                "/path/to/SnakeGameBoard.ets:116:20\n"
                "> hvigor ERROR: BUILD FAILED in 2 s 582 ms\n"
            )
        }
        mock_hvigor_cls.return_value = mock_hvigor

        result = await build.build_app('/path/to/project')

        assert result['error_count'] == 1
        assert result['errors'][0]['line'] == 116
        assert result['errors'][0]['message'] == "';' expected."
        assert "Error Message: ';' expected." in result['error']
        assert '> hvigor ERROR: BUILD FAILED in 2 s 582 ms' in result['error']


class TestInstallApp:
    """install_app 测试"""

    @pytest.mark.asyncio
    async def test_install_success(self, mock_hdc: MagicMock):
        """安装成功"""
        from harmonyos_mcp.tools import build

        result = await build.install_app('/path/to/app.hap')

        assert result['success'] is True
        assert result['device_id'] == 'device_001'
        assert result['hap_path'] == '/path/to/app.hap'
        mock_hdc.install_app.assert_called_once()

    @pytest.mark.asyncio
    async def test_install_to_specific_device(self, mock_hdc: MagicMock):
        """安装到指定设备"""
        from harmonyos_mcp.tools import build

        result = await build.install_app('/path/to/app.hap', device_id='device_002')

        assert result['device_id'] == 'device_002'
        mock_hdc.install_app.assert_called_with('device_002', '/path/to/app.hap')

    @pytest.mark.asyncio
    async def test_install_fails_when_no_device(self, no_device_mock: MagicMock):
        """无设备时安装失败"""
        from harmonyos_mcp.tools import build

        result = await build.install_app('/path/to/app.hap')

        assert result['success'] is False
        assert '没有找到' in result['error']


class TestRunApp:
    """run_app 测试"""

    @pytest.mark.asyncio
    async def test_auto_detect_ability(self, mock_hdc: MagicMock):
        """自动检测主 Ability"""
        from harmonyos_mcp.tools import build

        result = await build.run_app('com.example.app')

        assert result['success'] is True
        assert result['ability_name'] == 'MainAbility'
        assert result['module_name'] == 'entry'
        assert result['auto_detected'] is True

    @pytest.mark.asyncio
    async def test_use_specified_ability(self, mock_hdc: MagicMock):
        """使用指定的 Ability"""
        from harmonyos_mcp.tools import build

        result = await build.run_app(
            'com.example.app',
            ability_name='CustomAbility',
            module_name='feature'
        )

        assert result['ability_name'] == 'CustomAbility'
        assert result['module_name'] == 'feature'
        assert result['auto_detected'] is False

    @pytest.mark.asyncio
    async def test_use_default_ability_when_detection_fails(self, mock_hdc: MagicMock):
        """检测失败时使用默认 Ability"""
        from harmonyos_mcp.tools import build

        mock_hdc.get_main_ability.return_value = {
            'success': False,
            'error': 'Package not found'
        }

        result = await build.run_app('com.example.app')

        assert result['ability_name'] == 'EntryAbility'
        assert result['module_name'] == 'entry'
        assert result['auto_detected'] is False

    @pytest.mark.asyncio
    async def test_run_fails_when_no_device(self, no_device_mock: MagicMock):
        """无设备时运行失败"""
        from harmonyos_mcp.tools import build

        result = await build.run_app('com.example.app')

        assert result['success'] is False


class TestUninstallApp:
    """uninstall_app 测试"""

    @pytest.mark.asyncio
    async def test_uninstall_success(self, mock_hdc: MagicMock):
        """卸载成功"""
        from harmonyos_mcp.tools import build

        result = await build.uninstall_app('com.example.app')

        assert result['success'] is True
        assert result['bundle_name'] == 'com.example.app'
        mock_hdc.uninstall_app.assert_called_once()

    @pytest.mark.asyncio
    async def test_uninstall_from_specific_device(self, mock_hdc: MagicMock):
        """从指定设备卸载"""
        from harmonyos_mcp.tools import build

        result = await build.uninstall_app('com.example.app', device_id='device_002')

        mock_hdc.uninstall_app.assert_called_with('device_002', 'com.example.app')
