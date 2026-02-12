"""
重试装饰器模块

提供带指数退避的重试机制，支持异常捕获和返回值检测两种重试策略。
支持 async/sync 双模式。
"""
import asyncio
import functools
import inspect
import time
from typing import Tuple, Type, Callable, Optional

from loguru import logger


def retry(
    max_retries: int = None,
    delay: float = None,
    backoff: float = 2.0,
    max_delay: float = 30.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    should_retry: Optional[Callable] = None,
):
    """
    带指数退避的重试装饰器（支持 async/sync）

    支持两种重试触发方式：
    1. 异常捕获：捕获指定类型的异常后重试
    2. 返回值检测：通过 should_retry 回调检查返回值决定是否重试

    Args:
        max_retries: 最大重试次数（默认使用 Config.MAX_RETRIES）
        delay: 初始重试间隔秒数（默认使用 Config.RETRY_DELAY）
        backoff: 退避乘数，每次重试间隔 = 上次间隔 * backoff
        max_delay: 最大重试间隔秒数
        exceptions: 触发重试的异常类型元组
        should_retry: 可选回调，接收函数返回值，返回 True 表示需要重试

    Example:
        # 异常触发重试
        @retry(exceptions=(ConnectionError, TimeoutError))
        def fetch_data():
            ...

        # 返回值触发重试
        @retry(should_retry=lambda r: not r.get('success'))
        def execute_cmd():
            ...

        # 异步函数重试
        @retry(exceptions=(ConnectionError,))
        async def async_fetch():
            ...
    """
    def decorator(func):
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                from ..config import Config

                _max_retries = max_retries if max_retries is not None else Config.MAX_RETRIES
                _delay = delay if delay is not None else Config.RETRY_DELAY

                last_exception = None
                last_result = None
                current_delay = _delay

                for attempt in range(_max_retries + 1):
                    try:
                        result = await func(*args, **kwargs)

                        # 返回值检测重试
                        if should_retry and attempt < _max_retries and should_retry(result):
                            last_result = result
                            logger.warning(
                                f"[Retry] {func.__name__} 第{attempt + 1}/{_max_retries + 1}次尝试"
                                f"返回需重试的结果, {current_delay:.1f}s 后重试"
                            )
                            await asyncio.sleep(current_delay)
                            current_delay = min(current_delay * backoff, max_delay)
                            continue

                        if attempt > 0:
                            logger.info(
                                f"[Retry] {func.__name__} 在第{attempt + 1}次尝试后成功"
                            )
                        return result

                    except exceptions as e:
                        last_exception = e
                        if attempt < _max_retries:
                            logger.warning(
                                f"[Retry] {func.__name__} 第{attempt + 1}/{_max_retries + 1}次尝试"
                                f"失败: {e}, {current_delay:.1f}s 后重试"
                            )
                            await asyncio.sleep(current_delay)
                            current_delay = min(current_delay * backoff, max_delay)
                        else:
                            logger.error(
                                f"[Retry] {func.__name__} 在{_max_retries + 1}次尝试后仍失败: {e}"
                            )
                            raise

                if last_result is not None:
                    logger.error(
                        f"[Retry] {func.__name__} 在{_max_retries + 1}次尝试后"
                        f"仍返回需重试的结果"
                    )
                    return last_result

                if last_exception:
                    raise last_exception

            return async_wrapper
        else:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                from ..config import Config

                _max_retries = max_retries if max_retries is not None else Config.MAX_RETRIES
                _delay = delay if delay is not None else Config.RETRY_DELAY

                last_exception = None
                last_result = None
                current_delay = _delay

                for attempt in range(_max_retries + 1):
                    try:
                        result = func(*args, **kwargs)

                        # 返回值检测重试
                        if should_retry and attempt < _max_retries and should_retry(result):
                            last_result = result
                            logger.warning(
                                f"[Retry] {func.__name__} 第{attempt + 1}/{_max_retries + 1}次尝试"
                                f"返回需重试的结果, {current_delay:.1f}s 后重试"
                            )
                            time.sleep(current_delay)
                            current_delay = min(current_delay * backoff, max_delay)
                            continue

                        # 成功（首次或重试后成功）
                        if attempt > 0:
                            logger.info(
                                f"[Retry] {func.__name__} 在第{attempt + 1}次尝试后成功"
                            )
                        return result

                    except exceptions as e:
                        last_exception = e
                        if attempt < _max_retries:
                            logger.warning(
                                f"[Retry] {func.__name__} 第{attempt + 1}/{_max_retries + 1}次尝试"
                                f"失败: {e}, {current_delay:.1f}s 后重试"
                            )
                            time.sleep(current_delay)
                            current_delay = min(current_delay * backoff, max_delay)
                        else:
                            logger.error(
                                f"[Retry] {func.__name__} 在{_max_retries + 1}次尝试后仍失败: {e}"
                            )
                            raise

                # should_retry 耗尽重试次数后返回最后的结果
                if last_result is not None:
                    logger.error(
                        f"[Retry] {func.__name__} 在{_max_retries + 1}次尝试后"
                        f"仍返回需重试的结果"
                    )
                    return last_result

                # 不应到达此处，但作为安全兜底
                if last_exception:
                    raise last_exception

            return wrapper
    return decorator


def is_transient_hdc_failure(result: dict) -> bool:
    """
    判断 hdc 命令执行结果是否为瞬态失败（值得重试）

    瞬态失败包括：连接超时、设备通信中断等。
    永久性失败（如命令语法错误）不应重试。

    Args:
        result: _execute_command 返回的结果字典

    Returns:
        True 表示是瞬态失败，应该重试
    """
    if result.get('success'):
        return False

    stderr = result.get('stderr', '')
    # 瞬态失败的特征模式
    transient_patterns = [
        'timeout', 'timed out', '超时',
        'connect server failed', 'connection refused', 'connection reset',
        'device not respond', 'device not found',
        'cannot connect', 'broken pipe',
        'resource temporarily unavailable',
    ]
    stderr_lower = stderr.lower()
    return any(pattern in stderr_lower for pattern in transient_patterns)
