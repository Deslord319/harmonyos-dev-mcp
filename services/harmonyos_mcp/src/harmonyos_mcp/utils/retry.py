"""
重试装饰器模块

提供 HDC 特有的重试判断逻辑。
"""
from common.utils.retry import retry


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
    transient_patterns = [
        'timeout', 'timed out', '超时',
        'connect server failed', 'connection refused', 'connection reset',
        'device not respond', 'device not found',
        'cannot connect', 'broken pipe',
        'resource temporarily unavailable',
    ]
    stderr_lower = stderr.lower()
    return any(pattern in stderr_lower for pattern in transient_patterns)
