"""
Tests for retry behavior and tool registration.
"""

import time

import pytest

from harmonyos_mcp.utils.retry import is_transient_hdc_failure, retry
from common.tools.registry import clear_registry, get_registered_tools, get_tool_summary, mcp_tool


class TestRetry:
    def test_no_retry_on_success(self):
        call_count = 0

        @retry(max_retries=3, delay=0.01, exceptions=(ValueError,))
        def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = succeed()
        assert result == "ok"
        assert call_count == 1

    def test_retry_on_exception(self):
        call_count = 0

        @retry(max_retries=2, delay=0.01, exceptions=(ValueError,))
        def fail_twice_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("transient error")
            return "ok"

        result = fail_twice_then_succeed()
        assert result == "ok"
        assert call_count == 3

    def test_raises_after_max_retries(self):
        call_count = 0

        @retry(max_retries=2, delay=0.01, exceptions=(ValueError,))
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("permanent error")

        with pytest.raises(ValueError, match="permanent error"):
            always_fail()
        assert call_count == 3

    def test_no_retry_on_unmatched_exception(self):
        call_count = 0

        @retry(max_retries=3, delay=0.01, exceptions=(ValueError,))
        def raise_type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("wrong type")

        with pytest.raises(TypeError, match="wrong type"):
            raise_type_error()
        assert call_count == 1

    def test_should_retry_predicate(self):
        call_count = 0

        @retry(max_retries=2, delay=0.01, should_retry=lambda r: not r.get("success"))
        def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                return {"success": False, "error": "transient"}
            return {"success": True, "data": "ok"}

        result = fail_then_succeed()
        assert result["success"] is True
        assert call_count == 2

    def test_should_retry_exhausted(self):
        call_count = 0

        @retry(max_retries=2, delay=0.01, should_retry=lambda r: not r.get("success"))
        def always_fail_result():
            nonlocal call_count
            call_count += 1
            return {"success": False, "error": "always fail"}

        result = always_fail_result()
        assert result["success"] is False
        assert call_count == 3

    def test_exponential_backoff(self):
        timestamps = []

        @retry(max_retries=2, delay=0.05, backoff=2.0, exceptions=(ValueError,))
        def track_timing():
            timestamps.append(time.time())
            if len(timestamps) < 3:
                raise ValueError("retry")
            return "ok"

        track_timing()
        assert len(timestamps) == 3
        gap1 = timestamps[1] - timestamps[0]
        gap2 = timestamps[2] - timestamps[1]
        assert gap1 >= 0.04
        assert gap2 >= gap1 * 1.5


class TestIsTransientHdcFailure:
    def test_success_result_not_transient(self):
        assert is_transient_hdc_failure({"success": True}) is False

    def test_timeout_is_transient(self):
        assert is_transient_hdc_failure({"success": False, "stderr": "命令执行超时(30秒"}) is True

    def test_connection_refused_is_transient(self):
        assert is_transient_hdc_failure({"success": False, "stderr": "Connect server failed"}) is True

    def test_permanent_error_not_transient(self):
        assert is_transient_hdc_failure({"success": False, "stderr": "Invalid command syntax"}) is False

    def test_empty_stderr_not_transient(self):
        assert is_transient_hdc_failure({"success": False, "stderr": ""}) is False


class TestRegistry:
    def setup_method(self):
        self._original = get_registered_tools()
        clear_registry()

    def teardown_method(self):
        clear_registry()
        from common.tools.registry import _registry

        _registry.extend(self._original)

    def test_mcp_tool_registers_function(self):
        @mcp_tool(category="test")
        def my_tool():
            return "ok"

        tools = get_registered_tools()
        assert len(tools) == 1
        assert tools[0].func is my_tool
        assert tools[0].category == "test"

    def test_mcp_tool_preserves_function(self):
        @mcp_tool(category="test")
        def add(a, b):
            return a + b

        assert add(1, 2) == 3
        assert add.__name__ == "add"

    def test_mcp_tool_sets_category_attribute(self):
        @mcp_tool(category="device")
        def my_tool():
            pass

        assert my_tool._mcp_category == "device"

    def test_multiple_tools_registered(self):
        @mcp_tool(category="a")
        def tool_a():
            pass

        @mcp_tool(category="b")
        def tool_b():
            pass

        @mcp_tool(category="a")
        def tool_c():
            pass

        tools = get_registered_tools()
        assert len(tools) == 3

    def test_get_tool_summary(self):
        @mcp_tool(category="device")
        def t1():
            pass

        @mcp_tool(category="device")
        def t2():
            pass

        @mcp_tool(category="build")
        def t3():
            pass

        summary = get_tool_summary()
        assert summary["total"] == 3
        assert summary["categories"]["device"] == 2
        assert summary["categories"]["build"] == 1

    def test_clear_registry(self):
        @mcp_tool(category="test")
        def t():
            pass

        assert len(get_registered_tools()) == 1
        clear_registry()
        assert len(get_registered_tools()) == 0


class TestRealToolRegistration:
    def test_all_tools_registered(self):
        from harmonyos_mcp.tools import build, e2e, general, ui  # noqa: F401
        from harmonyos_mcp.tools.log import query as log_query  # noqa: F401

        tools = get_registered_tools()
        summary = get_tool_summary()

        assert tools
        assert summary["total"] == 18, (
            f"Expected 18 tools, got {summary['total']}. "
            f"Categories: {summary['categories']}"
        )

    def test_categories_correct(self):
        from harmonyos_mcp.tools import build, e2e, general, ui  # noqa: F401
        from harmonyos_mcp.tools.log import query as log_query  # noqa: F401

        summary = get_tool_summary()
        expected = {
            "build": 4,
            "general": 3,
            "ui": 8,
            "e2e": 3,
        }
        assert summary["categories"] == expected, (
            f"Category mismatch. Expected: {expected}, actual: {summary['categories']}"
        )
