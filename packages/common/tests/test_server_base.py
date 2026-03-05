"""
ServerBase 扩展功能完整测试套件

测试错误处理集成、on_error 回调、向后兼容性
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from common.server.base import create_server, run_server, _wrap_with_error_handler
from common.tools.registry import clear_registry, mcp_tool
from common.exceptions import MCPError


class TestServerErrorHandlingIntegration:
    """测试服务器错误处理集成"""

    def test_error_handler_catches_dict_error(self):
        """测试错误处理器捕获字典错误"""
        clear_registry()

        @mcp_tool(category="test")
        def failing_tool():
            return {"success": False, "error": "Test error", "error_code": "TEST_ERROR"}

        on_error_mock = Mock()
        server = create_server("test-server", enable_error_handler=True, on_error=on_error_mock)

        assert server is not None
        assert on_error_mock.call_count == 0

    def test_error_handler_catches_mcp_error(self):
        """测试错误处理器捕获 MCP 错误"""
        clear_registry()

        @mcp_tool(category="test")
        def mcp_error_tool():
            raise MCPError("MCP error occurred", "MCP_ERROR")

        on_error_mock = Mock()
        server = create_server("test-server", enable_error_handler=True, on_error=on_error_mock)

        assert server is not None
        assert on_error_mock.call_count == 0

    def test_error_handler_catches_exception(self):
        """测试错误处理器捕获通用异常"""
        clear_registry()

        @mcp_tool(category="test")
        def exception_tool():
            raise ValueError("Unexpected error")

        on_error_mock = Mock()
        server = create_server("test-server", enable_error_handler=True, on_error=on_error_mock)

        assert server is not None
        assert on_error_mock.call_count == 0

    def test_error_handler_disabled(self):
        """测试禁用错误处理器"""
        clear_registry()

        @mcp_tool(category="test")
        def failing_tool():
            return {"success": False, "error": "Test error"}

        server = create_server("test-server", enable_error_handler=False)

        assert server is not None


class TestOnErrorCallback:
    """测试 on_error 回调"""

    def test_on_error_called_with_dict_error(self):
        """测试字典错误触发 on_error 回调"""
        clear_registry()

        @mcp_tool(category="test")
        def failing_tool():
            return {"success": False, "error": "Test error", "error_code": "TEST_ERROR"}

        on_error_mock = Mock()
        server = create_server("test-server", enable_error_handler=True, on_error=on_error_mock)

        wrapped_tool = None
        for tool in server._tools.values():
            wrapped_tool = tool
            break

        if wrapped_tool:
            result = wrapped_tool()
            assert result["success"] == False
            assert result["error"] == "Test error"

    def test_on_error_called_with_mcp_error(self):
        """测试 MCP 错误触发 on_error 回调"""
        clear_registry()

        @mcp_tool(category="test")
        def mcp_error_tool():
            raise MCPError("MCP error occurred", "MCP_ERROR")

        on_error_mock = Mock()
        server = create_server("test-server", enable_error_handler=True, on_error=on_error_mock)

        wrapped_tool = None
        for tool in server._tools.values():
            wrapped_tool = tool
            break

        if wrapped_tool:
            result = wrapped_tool()
            assert result["structuredContent"]["ok"] is False
            assert result["structuredContent"]["error"]["detail"] == "MCP error occurred"
            assert result["structuredContent"]["error"]["code"] == "MCP_ERROR"

    def test_on_error_called_with_exception(self):
        """测试异常触发 on_error 回调"""
        clear_registry()

        @mcp_tool(category="test")
        def exception_tool():
            raise ValueError("Unexpected error")

        on_error_mock = Mock()
        server = create_server("test-server", enable_error_handler=True, on_error=on_error_mock)

        wrapped_tool = None
        for tool in server._tools.values():
            wrapped_tool = tool
            break

        if wrapped_tool:
            result = wrapped_tool()
            assert result["structuredContent"]["ok"] is False
            assert result["structuredContent"]["error"]["detail"] == "Unexpected error"
            assert result["structuredContent"]["error"]["code"] == "UNEXPECTED_ERROR"

    def test_on_error_not_called_on_success(self):
        """测试成功时不调用 on_error"""
        clear_registry()

        @mcp_tool(category="test")
        def success_tool():
            return {"success": True, "data": "test"}

        on_error_mock = Mock()
        server = create_server("test-server", enable_error_handler=True, on_error=on_error_mock)

        wrapped_tool = None
        for tool in server._tools.values():
            wrapped_tool = tool
            break

        if wrapped_tool:
            result = wrapped_tool()
            assert result["success"] == True
            assert on_error_mock.call_count == 0

    def test_on_error_callback_signature(self):
        """测试 on_error 回调签名"""
        clear_registry()

        @mcp_tool(category="test")
        def failing_tool():
            return {"success": False, "error": "Test error", "error_code": "TEST_ERROR"}

        def error_callback(message, code):
            assert isinstance(message, str)
            assert isinstance(code, str)
            assert message == "Test error"
            assert code == "TEST_ERROR"

        server = create_server("test-server", enable_error_handler=True, on_error=error_callback)
        assert server is not None

    def test_on_error_with_none_callback(self):
        """测试 on_error 为 None"""
        clear_registry()

        @mcp_tool(category="test")
        def failing_tool():
            return {"success": False, "error": "Test error"}

        server = create_server("test-server", enable_error_handler=True, on_error=None)
        assert server is not None


class TestWrapWithErrorHandler:
    """测试错误处理包装器"""

    def test_wrapper_preserves_function_name(self):
        """测试包装器保留函数名"""

        def test_func():
            return {"success": True}

        wrapped = _wrap_with_error_handler(test_func, None)

        assert wrapped.__name__ == test_func.__name__

    def test_wrapper_preserves_docstring(self):
        """测试包装器保留文档字符串"""

        def test_func():
            """Test function docstring"""
            return {"success": True}

        wrapped = _wrap_with_error_handler(test_func, None)

        assert wrapped.__doc__ == test_func.__doc__

    def test_wrapper_with_success_result(self):
        """测试包装器处理成功结果"""

        def test_func():
            return {"success": True, "data": "test"}

        wrapped = _wrap_with_error_handler(test_func, None)
        result = wrapped()

        assert result["success"] == True
        assert result["data"] == "test"

    def test_wrapper_with_failure_result(self):
        """测试包装器处理失败结果"""

        def test_func():
            return {
                "structuredContent": {
                    "tool": "test_tool",
                    "ok": False,
                    "result": None,
                    "error": {"code": "TEST_ERROR", "detail": "Test error"},
                    "meta": {"request_id": "x", "duration_ms": 1, "timestamp": "2026-03-05T00:00:00Z"},
                }
            }

        on_error_mock = Mock()
        wrapped = _wrap_with_error_handler(test_func, on_error_mock)
        result = wrapped()

        assert result["structuredContent"]["ok"] is False
        assert result["structuredContent"]["error"]["detail"] == "Test error"
        assert on_error_mock.call_count == 1

    def test_wrapper_with_mcp_error(self):
        """测试包装器处理 MCP 错误"""

        def test_func():
            raise MCPError("MCP error", "MCP_CODE")

        on_error_mock = Mock()
        wrapped = _wrap_with_error_handler(test_func, on_error_mock)
        result = wrapped()

        assert result["structuredContent"]["ok"] is False
        assert result["structuredContent"]["error"]["detail"] == "MCP error"
        assert result["structuredContent"]["error"]["code"] == "MCP_CODE"
        assert on_error_mock.call_count == 1

    def test_wrapper_with_exception(self):
        """测试包装器处理异常"""

        def test_func():
            raise ValueError("Test exception")

        on_error_mock = Mock()
        wrapped = _wrap_with_error_handler(test_func, on_error_mock)
        result = wrapped()

        assert result["structuredContent"]["ok"] is False
        assert result["structuredContent"]["error"]["detail"] == "Test exception"
        assert result["structuredContent"]["error"]["code"] == "UNEXPECTED_ERROR"
        assert on_error_mock.call_count == 1

    def test_wrapper_with_missing_error_code(self):
        """测试包装器处理缺失错误代码"""

        def test_func():
            return {
                "structuredContent": {
                    "tool": "test_tool",
                    "ok": False,
                    "result": None,
                    "error": {"detail": "Test error"},
                    "meta": {"request_id": "x", "duration_ms": 1, "timestamp": "2026-03-05T00:00:00Z"},
                }
            }

        on_error_mock = Mock()
        wrapped = _wrap_with_error_handler(test_func, on_error_mock)
        result = wrapped()

        assert result["structuredContent"]["ok"] is False
        assert on_error_mock.call_count == 1


class TestRunServer:
    """测试运行服务器"""

    def test_run_server_with_config(self):
        """测试带配置运行服务器"""
        clear_registry()

        @mcp_tool(category="test")
        def dummy_tool():
            return {"success": True}

        from common.config.base import ConfigBase

        ConfigBase._initialized = False

        server = create_server("test-server", enable_error_handler=False)

        on_startup_mock = Mock()
        on_error_mock = Mock()
        setup_logger_mock = Mock()

        with patch.object(server, "run", side_effect=KeyboardInterrupt):
            run_server(
                server=server,
                config_class=ConfigBase,
                setup_logger_func=setup_logger_mock,
                on_startup=on_startup_mock,
                on_error=on_error_mock,
            )

        assert setup_logger_mock.call_count == 1
        assert on_startup_mock.call_count == 1
        assert ConfigBase._initialized

    def test_run_server_without_config(self):
        """测试不带配置运行服务器"""
        clear_registry()

        @mcp_tool(category="test")
        def dummy_tool():
            return {"success": True}

        server = create_server("test-server", enable_error_handler=False)

        on_startup_mock = Mock()
        setup_logger_mock = Mock()

        with patch.object(server, "run", side_effect=KeyboardInterrupt):
            run_server(
                server=server,
                config_class=None,
                setup_logger_func=setup_logger_mock,
                on_startup=on_startup_mock,
                on_error=None,
            )

        assert setup_logger_mock.call_count == 1
        assert on_startup_mock.call_count == 1

    def test_run_server_startup_failure(self):
        """测试启动失败处理"""
        clear_registry()

        @mcp_tool(category="test")
        def dummy_tool():
            return {"success": True}

        server = create_server("test-server", enable_error_handler=False)

        def failing_startup():
            raise Exception("Startup failed")

        on_error_mock = Mock()
        setup_logger_mock = Mock()

        with patch.object(server, "run", side_effect=KeyboardInterrupt):
            run_server(
                server=server,
                config_class=None,
                setup_logger_func=setup_logger_mock,
                on_startup=failing_startup,
                on_error=on_error_mock,
            )

        assert on_error_mock.call_count == 1

    def test_run_server_keyboard_interrupt(self):
        """测试键盘中断处理"""
        clear_registry()

        @mcp_tool(category="test")
        def dummy_tool():
            return {"success": True}

        server = create_server("test-server", enable_error_handler=False)

        setup_logger_mock = Mock()

        with patch.object(server, "run", side_effect=KeyboardInterrupt):
            run_server(
                server=server,
                config_class=None,
                setup_logger_func=setup_logger_mock,
                on_startup=None,
                on_error=None,
            )

        assert setup_logger_mock.call_count == 1


class TestServerCoreBehavior:
    """测试服务器向后兼容性"""

    def test_create_server_without_optional_params(self):
        """测试不带可选参数创建服务器"""
        clear_registry()

        @mcp_tool(category="test")
        def dummy_tool():
            return {"success": True}

        server = create_server("test-server")

        assert server is not None

    def test_create_server_with_tool_modules(self):
        """测试带工具模块创建服务器"""
        clear_registry()

        @mcp_tool(category="test")
        def dummy_tool():
            return {"success": True}

        server = create_server("test-server", tool_modules=[])

        assert server is not None

    def test_run_server_without_callbacks(self):
        """测试不带回调运行服务器"""
        clear_registry()

        @mcp_tool(category="test")
        def dummy_tool():
            return {"success": True}

        server = create_server("test-server", enable_error_handler=False)

        with patch.object(server, "run", side_effect=KeyboardInterrupt):
            run_server(
                server=server,
                config_class=None,
                setup_logger_func=None,
                on_startup=None,
                on_error=None,
            )

    def test_multiple_servers_independent(self):
        """测试多个服务器独立"""
        clear_registry()

        @mcp_tool(category="test1")
        def tool1():
            return {"success": True}

        server1 = create_server("server1", enable_error_handler=False)

        @mcp_tool(category="test2")
        def tool2():
            return {"success": True}

        server2 = create_server("server2", enable_error_handler=False)

        assert server1 is not None
        assert server2 is not None
        assert server1 != server2


class TestServerEdgeCases:
    """测试服务器边界情况"""

    def test_empty_server_name(self):
        """测试空服务器名称"""
        clear_registry()

        server = create_server("", enable_error_handler=False)

        assert server is not None

    def test_no_registered_tools(self):
        """测试无注册工具"""
        clear_registry()

        server = create_server("test-server", enable_error_handler=False)

        assert server is not None

    def test_on_error_with_complex_exception(self):
        """测试复杂异常处理"""
        clear_registry()

        @mcp_tool(category="test")
        def complex_error_tool():
            try:
                raise ValueError("Inner error")
            except ValueError as e:
                raise RuntimeError(f"Wrapped: {e}")

        on_error_mock = Mock()
        server = create_server("test-server", enable_error_handler=True, on_error=on_error_mock)

        wrapped_tool = None
        for tool in server._tools.values():
            wrapped_tool = tool
            break

        if wrapped_tool:
            result = wrapped_tool()
            assert result["structuredContent"]["ok"] is False
            assert "Wrapped" in result["structuredContent"]["error"]["detail"]

    def test_wrapper_with_none_return(self):
        """测试包装器处理 None 返回"""

        def test_func():
            return None

        wrapped = _wrap_with_error_handler(test_func, None)
        result = wrapped()

        assert result is None

    def test_wrapper_with_non_dict_return(self):
        """测试包装器处理非字典返回"""

        def test_func():
            return "string result"

        wrapped = _wrap_with_error_handler(test_func, None)
        result = wrapped()

        assert result == "string result"
