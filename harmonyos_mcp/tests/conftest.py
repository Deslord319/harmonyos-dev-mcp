"""
pytest 配置和 fixtures

提供测试用的公共 fixtures 和配置。
"""
import pytest
from typing import Generator
from unittest.mock import MagicMock
from loguru import logger
import sys


# ============================================================================
# 测试日志配置
# ============================================================================
def pytest_configure(config):
    """pytest 配置钩子，在测试开始前配置日志"""
    # 移除默认 handler，避免测试时输出过多 DEBUG 日志
    logger.remove()
    # 测试时使用 WARNING 级别，减少日志噪音
    logger.add(
        sys.stderr,
        format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level="WARNING",
        colorize=True,
    )


@pytest.fixture(autouse=True)
def reset_container():
    """每个测试后重置依赖容器"""
    yield
    from harmonyos_mcp.container import Container
    Container.reset()


@pytest.fixture
def mock_hdc() -> Generator[MagicMock, None, None]:
    """
    Mock HdcWrapper
    
    提供默认的返回值，可以在测试中覆盖。
    """
    from harmonyos_mcp.utils.hdc import HdcWrapper
    from harmonyos_mcp.container import Container
    
    mock = MagicMock(spec=HdcWrapper)
    
    # 默认返回值
    mock.list_devices.return_value = ['device_001', 'device_002']
    mock.install_app.return_value = True
    mock.uninstall_app.return_value = True
    mock.get_main_ability.return_value = {
        'success': True,
        'ability_name': 'MainAbility',
        'module_name': 'entry'
    }
    mock.start_app.return_value = {
        'success': True,
        'command_success': True,
        'window_found': True
    }
    mock.list_packages.return_value = {
        'success': True,
        'packages': ['com.example.app1', 'com.example.app2'],
        'count': 2
    }
    mock.get_package_info.return_value = {
        'success': True,
        'abilities': [
            {'name': 'MainAbility', 'module': 'entry', 'type': 'page'}
        ],
        'modules': ['entry'],
        'main_ability': {'ability_name': 'MainAbility', 'module_name': 'entry'}
    }
    mock.get_window_list.return_value = {
        'success': True,
        'windows': [
            {'window_id': 1, 'bundle_name': 'com.example.app', 'is_visible': True}
        ]
    }
    mock.get_ui_tree_raw.return_value = {
        'success': True,
        'ui_tree': {'type': 'Root', 'children': []}
    }
    mock.get_realtime_logs.return_value = "01-31 10:00:00.123  1234  1234 I MyTag: Test log"
    mock.get_app_pid.return_value = 1234
    
    # 注入到容器
    Container.register(HdcWrapper, mock)
    
    yield mock


@pytest.fixture
def single_device_mock(mock_hdc: MagicMock) -> MagicMock:
    """模拟单设备场景"""
    mock_hdc.list_devices.return_value = ['device_001']
    return mock_hdc


@pytest.fixture
def no_device_mock(mock_hdc: MagicMock) -> MagicMock:
    """模拟无设备场景"""
    mock_hdc.list_devices.return_value = []
    return mock_hdc


@pytest.fixture
def mock_ui_operations() -> Generator[MagicMock, None, None]:
    """Mock UiTestWrapper"""
    from harmonyos_mcp.utils.wrappers.ui_operations import UiTestWrapper
    from harmonyos_mcp.container import Container
    
    mock = MagicMock(spec=UiTestWrapper)
    
    # 默认返回值
    mock.click.return_value = {'success': True, 'x': 100, 'y': 200}
    mock.double_click.return_value = {'success': True, 'x': 100, 'y': 200}
    mock.long_click.return_value = {'success': True}
    mock.swipe.return_value = {'success': True}
    mock.swipe_direction.return_value = {'success': True, 'direction': 'up'}
    mock.input_text.return_value = {'success': True}
    mock.press_key.return_value = {'success': True}
    mock.find_element.return_value = {
        'success': True,
        'elements': [{'x': 100, 'y': 200, 'text': 'Button', 'type': 'Button'}],
        'count': 1
    }
    
    Container.register(UiTestWrapper, mock)
    
    yield mock
