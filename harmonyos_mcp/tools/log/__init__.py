"""
日志模块

提供 HarmonyOS hilog 日志查询功能

子模块:
- parser: 日志解析器
- time_utils: 时间工具
- historian: 历史日志获取
- query: 主查询入口
"""

from .parser import LogParser, LogEntry
from .query import logs_query

__all__ = ['LogParser', 'LogEntry', 'logs_query']
