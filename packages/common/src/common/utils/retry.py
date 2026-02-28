"""
重试装饰器

提供带指数退避的重试机制，支持 async/sync 双模式。
"""
import asyncio
import functools
import inspect
import time
from typing import Tuple, Type, Callable, Optional
from loguru import logger


def retry(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    max_delay: float = 30.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    should_retry: Optional[Callable] = None,
):
    """
    带指数退避的重试装饰器

    Args:
        max_retries: 最大重试次数
        delay: 初始重试间隔秒数
        backoff: 退避乘数
        max_delay: 最大重试间隔
        exceptions: 触发重试的异常类型
        should_retry: 可选回调，检查返回值决定是否重试
    """
    def decorator(func):
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                current_delay = delay
                last_exception = None
                last_result = None

                for attempt in range(max_retries + 1):
                    try:
                        result = await func(*args, **kwargs)
                        if should_retry and attempt < max_retries and should_retry(result):
                            logger.warning(
                                f"[Retry] {func.__name__} 第{attempt + 1}次需重试, "
                                f"{current_delay:.1f}s 后重试"
                            )
                            await asyncio.sleep(current_delay)
                            current_delay = min(current_delay * backoff, max_delay)
                            continue
                        if attempt > 0:
                            logger.info(f"[Retry] {func.__name__} 第{attempt + 1}次成功")
                        return result
                    except exceptions as e:
                        last_exception = e
                        if attempt < max_retries:
                            logger.warning(
                                f"[Retry] {func.__name__} 第{attempt + 1}次失败: {e}, "
                                f"{current_delay:.1f}s 后重试"
                            )
                            await asyncio.sleep(current_delay)
                            current_delay = min(current_delay * backoff, max_delay)
                        else:
                            logger.error(
                                f"[Retry] {func.__name__} 在{max_retries + 1}次尝试后仍失败: {e}"
                            )
                            raise

                if last_result is not None:
                    return last_result
                if last_exception:
                    raise last_exception

            return async_wrapper
        else:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                current_delay = delay
                last_exception = None
                last_result = None

                for attempt in range(max_retries + 1):
                    try:
                        result = func(*args, **kwargs)
                        if should_retry and attempt < max_retries and should_retry(result):
                            logger.warning(
                                f"[Retry] {func.__name__} 第{attempt + 1}次需重试, "
                                f"{current_delay:.1f}s 后重试"
                            )
                            time.sleep(current_delay)
                            current_delay = min(current_delay * backoff, max_delay)
                            continue
                        if attempt > 0:
                            logger.info(f"[Retry] {func.__name__} 第{attempt + 1}次成功")
                        return result
                    except exceptions as e:
                        last_exception = e
                        if attempt < max_retries:
                            logger.warning(
                                f"[Retry] {func.__name__} 第{attempt + 1}次失败: {e}, "
                                f"{current_delay:.1f}s 后重试"
                            )
                            time.sleep(current_delay)
                            current_delay = min(current_delay * backoff, max_delay)
                        else:
                            logger.error(
                                f"[Retry] {func.__name__} 在{max_retries + 1}次尝试后仍失败: {e}"
                            )
                            raise

                if last_result is not None:
                    return last_result
                if last_exception:
                    raise last_exception

            return wrapper
    return decorator


def is_transient_error(result: dict) -> bool:
    """
    判断结果是否为瞬态错误（值得重试）

    瞬态错误包括：连接超时、设备通信中断等。
    永久性错误（如命令语法错误）不应重试。
    """
    if result.get("success"):
        return False

    stderr = result.get("stderr", "").lower()
    transient_patterns = [
        "timeout", "timed out", "超时",
        "connect", "connection refused", "connection reset",
        "device not respond", "device not found",
        "cannot connect", "broken pipe",
        "resource temporarily unavailable",
    ]
    return any(p in stderr for p in transient_patterns)
