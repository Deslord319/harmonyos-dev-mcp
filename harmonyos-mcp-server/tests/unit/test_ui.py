"""
UI 操作工具单元测试
"""
import pytest
from unittest.mock import MagicMock

pytestmark = pytest.mark.asyncio


class TestClickElement:
    """click_element 测试"""

    async def test_click_by_coordinates(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock):
        """通过坐标点击"""
        from harmonyos_mcp.tools import ui

        result = await ui.click_element(x=100, y=200)

        assert result['success'] is True
        mock_ui_operations.click.assert_called_once_with('device_001', 100, 200)

    async def test_click_by_text(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock):
        """通过文本查找并点击"""
        from harmonyos_mcp.tools import ui

        result = await ui.click_element(text='登录')

        assert result['success'] is True
        mock_ui_operations.find_element.assert_called_once()
        mock_ui_operations.click.assert_called_once()

    async def test_double_click(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock):
        """双击操作"""
        from harmonyos_mcp.tools import ui

        result = await ui.click_element(x=100, y=200, double_click=True)

        assert result['success'] is True
        mock_ui_operations.double_click.assert_called_once_with('device_001', 100, 200)

    async def test_click_element_not_found(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock):
        """元素未找到"""
        from harmonyos_mcp.tools import ui

        mock_ui_operations.find_element.return_value = {
            'success': True,
            'elements': [],
            'count': 0
        }

        result = await ui.click_element(text='不存在的按钮')

        assert result['success'] is False
        assert 'ELEMENT_NOT_FOUND' in result.get('error_code', '')

    async def test_click_requires_params(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock):
        """必须提供参数"""
        from harmonyos_mcp.tools import ui

        result = await ui.click_element()

        assert result['success'] is False
        assert 'MISSING_PARAMS' in result.get('error_code', '')


class TestSwipe:
    """swipe 测试"""

    async def test_swipe_by_coordinates(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock):
        """通过坐标滑动"""
        from harmonyos_mcp.tools import ui

        result = await ui.swipe(from_x=100, from_y=500, to_x=100, to_y=200)

        assert result['success'] is True
        mock_ui_operations.swipe.assert_called_once()

    async def test_swipe_by_direction(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock):
        """通过方向滑动"""
        from harmonyos_mcp.tools import ui

        result = await ui.swipe(direction='up')

        assert result['success'] is True
        mock_ui_operations.swipe_direction.assert_called_once_with('device_001', 'up', 600)

    async def test_swipe_with_custom_speed(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock):
        """自定义滑动速度"""
        from harmonyos_mcp.tools import ui

        result = await ui.swipe(direction='down', speed=1000)

        assert result['success'] is True
        mock_ui_operations.swipe_direction.assert_called_once_with('device_001', 'down', 1000)


class TestInputText:
    """input_text 测试"""

    async def test_input_by_coordinates(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock):
        """通过坐标输入"""
        from harmonyos_mcp.tools import ui

        result = await ui.input_text(x=100, y=200, text='Hello World')

        assert result['success'] is True
        mock_ui_operations.input_text.assert_called_once_with('device_001', 100, 200, 'Hello World')

    async def test_input_requires_text(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock):
        """必须提供文本"""
        from harmonyos_mcp.tools import ui

        result = await ui.input_text(x=100, y=200)

        assert result['success'] is False
        assert 'MISSING_TEXT' in result.get('error_code', '')


class TestPressKey:
    """press_key 测试"""

    async def test_press_home(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock):
        """按 Home 键"""
        from harmonyos_mcp.tools import ui

        result = await ui.press_key(key='Home')

        assert result['success'] is True
        mock_ui_operations.press_key.assert_called_once_with('device_001', 'Home')

    async def test_press_key_requires_key(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock):
        """必须提供按键"""
        from harmonyos_mcp.tools import ui

        result = await ui.press_key()

        assert result['success'] is False
        assert 'MISSING_KEY' in result.get('error_code', '')


class TestFindElement:
    """find_element 测试"""

    async def test_find_by_text(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock):
        """通过文本查找"""
        from harmonyos_mcp.tools import ui

        result = await ui.find_element(text='登录')

        assert result['success'] is True
        assert result['count'] == 1
        mock_ui_operations.find_element.assert_called_once()

    async def test_find_by_type(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock):
        """通过类型查找"""
        from harmonyos_mcp.tools import ui

        result = await ui.find_element(element_type='Button')

        assert result['success'] is True
        mock_ui_operations.find_element.assert_called_once()

    async def test_find_requires_criteria(self, mock_hdc: MagicMock, mock_ui_operations: MagicMock):
        """必须提供查找条件"""
        from harmonyos_mcp.tools import ui

        result = await ui.find_element()

        assert result['success'] is False
        assert 'MISSING_SEARCH_CRITERIA' in result.get('error_code', '')
