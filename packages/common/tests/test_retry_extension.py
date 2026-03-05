"""
Retry 扩展功能完整测试套件

测试 retry_on_transient_only 参数、瞬态错误重试、永久错误不
重试、向后兼容性
"""

import pytest
import asyncio
import time
from common.utils.retry import retry, ErrorClassifier, ErrorCategory


class TestRetryOnTransientOnly:
    """测试 retry_on_transient_only 参数"""

    def test_retry_on_transient_only_transient_sync(self):
        """测试同步函数 - 瞬态错误会重试"""
        call_count = 0

        @retry(max_retries=2, retry_on_transient_only=True)
        def fail_transient():
            nonlocal call_count
            call_count += 1
            raise Exception("connection timeout")

        with pytest.raises(Exception):
            fail_transient()

        assert call_count == 3

    def test_retry_on_transient_only_permanent_sync(self):
        """测试同步函数 - 永久错误不重试"""
        call_count = 0

        @retry(max_retries=2, retry_on_transient_only=True)
        def fail_permanent():
            nonlocal call_count
            call_count += 1
            raise Exception("syntax error")

        with pytest.raises(Exception):
            fail_permanent()

        assert call_count == 1

    def test_retry_on_transient_only_transient_async(self):
        """测试异步函数 - 瞬态错误会重试"""
        call_count = 0

        @retry(max_retries=2, retry_on_transient_only=True)
        async def fail_transient():
            nonlocal call_count
            call_count += 1
            raise Exception("connection timeout")

        with pytest.raises(Exception):
            asyncio.run(fail_transient())

        assert call_count == 3

    def test_retry_on_transient_only_permanent_async(self):
        """测试异步函数 - 永久错误不重试"""
        call_count = 0

        @retry(max_retries=2, retry_on_transient_only=True)
        async def fail_permanent():
            nonlocal call_count
            call_count += 1
            raise Exception("syntax error")

        with pytest.raises(Exception):
            asyncio.run(fail_permanent())

        assert call_count == 1

    def test_retry_on_transient_only_false_sync(self):
        """测试 retry_on_transient_only=False - 所有错误都重试"""
        call_count = 0

        @retry(max_retries=2, retry_on_transient_only=False)
        def fail_permanent():
            nonlocal call_count
            call_count += 1
            raise Exception("syntax error")

        with pytest.raises(Exception):
            fail_permanent()

        assert call_count == 3

    def test_retry_on_transient_only_false_async(self):
        """测试异步函数 retry_on_transient_only=False"""
        call_count = 0

        @retry(max_retries=2, retry_on_transient_only=False)
        async def fail_permanent():
            nonlocal call_count
            call_count += 1
            raise Exception("syntax error")

        with pytest.raises(Exception):
            asyncio.run(fail_permanent())

        assert call_count == 3


class TestRetryTransientErrors:
    """测试瞬态错误重试"""

    def test_retry_timeout_error(self):
        """测试超时错误重试"""
        call_count = 0

        @retry(max_retries=2, retry_on_transient_only=True)
        def timeout_func():
            nonlocal call_count
            call_count += 1
            raise Exception("operation timed out")

        with pytest.raises(Exception):
            timeout_func()

        assert call_count == 3

    def test_retry_connection_refused(self):
        """测试连接被拒绝重试"""
        call_count = 0

        @retry(max_retries=2, retry_on_transient_only=True)
        def connect_func():
            nonlocal call_count
            call_count += 1
            raise Exception("connection refused")

        with pytest.raises(Exception):
            connect_func()

        assert call_count == 3

    def test_retry_device_not_found(self):
        """测试设备未找到重试"""
        call_count = 0

        @retry(max_retries=2, retry_on_transient_only=True)
        def device_func():
            nonlocal call_count
            call_count += 1
            raise Exception("device not found")

        with pytest.raises(Exception):
            device_func()

        assert call_count == 3

    def test_retry_network_error(self):
        """测试网络错误重试"""
        call_count = 0

        @retry(max_retries=2, retry_on_transient_only=True)
        def network_func():
            nonlocal call_count
            call_count += 1
            raise Exception("network error")

        with pytest.raises(Exception):
            network_func()

        assert call_count == 3

    def test_retry_chinese_timeout(self):
        """测试中文超时错误重试"""
        call_count = 0

        @retry(max_retries=2, retry_on_transient_only=True)
        def chinese_timeout():
            nonlocal call_count
            call_count += 1
            raise Exception("连接超时")

        with pytest.raises(Exception):
            chinese_timeout()

        assert call_count == 3

    def test_retry_transient_then_success(self):
        """测试瞬态错误后成功"""
        call_count = 0

        @retry(max_retries=2, retry_on_transient_only=True)
        def eventually_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("connection timeout")
            return "success"

        result = eventually_succeed()

        assert result == "success"
        assert call_count == 2


class TestRetryPermanentErrors:
    """测试永久错误不重试"""

    def test_no_retry_syntax_error(self):
        """测试语法错误不重试"""
        call_count = 0

        @retry(max_retries=2, retry_on_transient_only=True)
        def syntax_error_func():
            nonlocal call_count
            call_count += 1
            raise Exception("syntax error")

        with pytest.raises(Exception):
            syntax_error_func()

        assert call_count == 1

    def test_no_retry_permission_denied(self):
        """测试权限错误不重试"""
        call_count = 0

        @retry(max_retries=2, retry_on_transient_only=True)
        def permission_func():
            nonlocal call_count
            call_count += 1
            raise Exception("permission denied")

        with pytest.raises(Exception):
            permission_func()

        assert call_count == 1

    def test_no_retry_validation_error(self):
        """测试验证错误不重试"""
        call_count = 0

        @retry(max_retries=2, retry_on_transient_only=True)
        def validation_func():
            nonlocal call_count
            call_count += 1
            raise Exception("validation failed")

        with pytest.raises(Exception):
            validation_func()

        assert call_count == 1

    def test_no_retry_unknown_error(self):
        """测试未知错误不重试"""
        call_count = 0

        @retry(max_retries=2, retry_on_transient_only=True)
        def unknown_error_func():
            nonlocal call_count
            call_count += 1
            raise Exception("unknown error")

        with pytest.raises(Exception):
            unknown_error_func()

        assert call_count == 1


class TestRetryCoreBehavior:
    """测试重试核心行为"""

    def test_default_retry_behavior(self):
        """测试默认重试行为（不使用 retry_on_transient_only）"""
        call_count = 0

        @retry(max_retries=2)
        def default_retry():
            nonlocal call_count
            call_count += 1
            raise Exception("any error")

        with pytest.raises(Exception):
            default_retry()

        assert call_count == 3

    def test_custom_exception_type(self):
        """测试自定义异常类型"""
        call_count = 0

        class CustomError(Exception):
            pass

        @retry(max_retries=2, exceptions=(CustomError,))
        def custom_exception_func():
            nonlocal call_count
            call_count += 1
            raise CustomError("custom error")

        with pytest.raises(CustomError):
            custom_exception_func()

        assert call_count == 3

    def test_should_retry_callback(self):
        """测试 should_retry 回调"""
        call_count = 0

        def should_retry_func(result):
            return result.get("retry", False)

        @retry(max_retries=2, should_retry=should_retry_func)
        def callback_retry():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                return {"retry": True}
            return {"retry": False}

        result = callback_retry()

        assert not result.get("retry")
        assert call_count == 2

    def test_exponential_backoff(self):
        """测试指数退避"""
        call_times = []
        start_time = time.time()

        @retry(max_retries=2, delay=0.1, backoff=2.0)
        def backoff_func():
            call_times.append(time.time() - start_time)
            raise Exception("error")

        with pytest.raises(Exception):
            backoff_func()

        assert len(call_times) == 3
        assert call_times[1] - call_times[0] >= 0.1
        assert call_times[2] - call_times[1] >= 0.2

    def test_max_delay(self):
        """测试最大延迟"""
        call_times = []
        start_time = time.time()

        @retry(max_retries=3, delay=0.1, backoff=10.0, max_delay=0.2)
        def max_delay_func():
            call_times.append(time.time() - start_time)
            raise Exception("error")

        with pytest.raises(Exception):
            max_delay_func()

        assert len(call_times) == 4
        for i in range(1, len(call_times)):
            delay = call_times[i] - call_times[i - 1]
            assert delay >= 0.1
            assert delay <= 0.25

    def test_successful_execution(self):
        """测试成功执行不重试"""
        call_count = 0

        @retry(max_retries=2)
        def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = success_func()

        assert result == "success"
        assert call_count == 1

    def test_async_successful_execution(self):
        """测试异步成功执行"""
        call_count = 0

        @retry(max_retries=2)
        async def async_success():
            nonlocal call_count
            call_count += 1
            return "async success"

        result = asyncio.run(async_success())

        assert result == "async success"
        assert call_count == 1


class TestRetryEdgeCases:
    """测试边界情况"""

    def test_zero_retries(self):
        """测试零次重试"""
        call_count = 0

        @retry(max_retries=0)
        def zero_retry():
            nonlocal call_count
            call_count += 1
            raise Exception("error")

        with pytest.raises(Exception):
            zero_retry()

        assert call_count == 1

    def test_negative_delay(self):
        """测试负延迟"""
        call_count = 0

        @retry(max_retries=2, delay=-1.0)
        def negative_delay():
            nonlocal call_count
            call_count += 1
            raise Exception("error")

        with pytest.raises(Exception):
            negative_delay()

        assert call_count == 3

    def test_zero_delay(self):
        """测试零延迟"""
        call_count = 0
        start_time = time.time()

        @retry(max_retries=2, delay=0)
        def zero_delay():
            nonlocal call_count
            call_count += 1
            raise Exception("error")

        with pytest.raises(Exception):
            zero_delay()

        elapsed = time.time() - start_time
        assert call_count == 3
        assert elapsed < 1.0

    def test_very_large_retries(self):
        """测试大量重试（但会快速失败）"""
        call_count = 0

        @retry(max_retries=100, delay=0)
        def large_retries():
            nonlocal call_count
            call_count += 1
            if call_count < 5:
                raise Exception("error")
            return "success"

        result = large_retries()

        assert result == "success"
        assert call_count == 5

    def test_exception_preservation(self):
        """测试异常保留"""
        original_error = ValueError("original error")

        @retry(max_retries=2, retry_on_transient_only=True)
        def raise_value_error():
            raise original_error

        with pytest.raises(ValueError) as exc_info:
            raise_value_error()

        assert str(exc_info.value) == "original error"

    def test_nested_retry_decorators(self):
        """测试嵌套重试装饰器"""
        outer_count = 0
        inner_count = 0

        @retry(max_retries=1)
        @retry(max_retries=1)
        def nested_retry():
            nonlocal outer_count, inner_count
            inner_count += 1
            outer_count += 1
            raise Exception("error")

        with pytest.raises(Exception):
            nested_retry()

        assert outer_count == 2
        assert inner_count == 2


class TestRetryWithDifferentExceptions:
    """测试不同异常类型"""

    def test_specific_exception_transient(self):
        """测试特定异常瞬态重试"""
        call_count = 0

        @retry(max_retries=2, retry_on_transient_only=True, exceptions=(ConnectionError,))
        def connection_error():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("connection timeout")

        with pytest.raises(ConnectionError):
            connection_error()

        assert call_count == 3

    def test_specific_exception_not_matched(self):
        """测试特定异常不匹配"""
        call_count = 0

        @retry(max_retries=2, retry_on_transient_only=True, exceptions=(ValueError,))
        def connection_error():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("connection timeout")

        with pytest.raises(ConnectionError):
            connection_error()

        assert call_count == 1

    def test_multiple_exception_types(self):
        """测试多个异常类型"""
        call_count = 0

        @retry(
            max_retries=2, retry_on_transient_only=True, exceptions=(ConnectionError, TimeoutError)
        )
        def multi_exception():
            nonlocal call_count
            call_count += 1
            raise TimeoutError("operation timed out")

        with pytest.raises(TimeoutError):
            multi_exception()

        assert call_count == 3


class TestRetryAsyncSpecific:
    """测试异步特定功能"""

    def test_async_with_await(self):
        """测试异步函数带 await"""
        call_count = 0

        @retry(max_retries=2, retry_on_transient_only=True)
        async def async_with_await():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            if call_count < 2:
                raise Exception("timeout")
            return "success"

        result = asyncio.run(async_with_await())

        assert result == "success"
        assert call_count == 2

    def test_async_concurrent(self):
        """测试并发异步重试"""
        call_count = 0

        @retry(max_retries=2, retry_on_transient_only=True)
        async def async_concurrent():
            nonlocal call_count
            call_count += 1
            raise Exception("timeout")

        with pytest.raises(Exception):
            asyncio.run(async_concurrent())

        assert call_count == 3
