"""
日志配置模块

使用 loguru 的 enqueue=True 实现异步日志写入，
避免 I/O 操作阻塞主事件循环（尤其在高频 hdc 命令场景下）。
"""
import sys
from pathlib import Path
from loguru import logger

from ..config import Config

# 项目根目录: harmonyos-mcp-server/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LOG_DIR = _PROJECT_ROOT / "logs"


def setup_logger():
    """
    配置日志系统

    关键特性：
    - enqueue=True: 日志写入在独立线程中异步执行，不阻塞主线程
    - 控制台输出 + 文件轮转输出双通道
    - 日志路径锚定到项目根目录，不依赖 CWD
    """
    # 移除默认处理器
    logger.remove()

    # 添加控制台输出（异步）
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=Config.LOG_LEVEL,
        colorize=True,
        enqueue=True,
    )

    # 添加文件输出（异步，路径锚定到项目根目录）
    logger.add(
        str(_LOG_DIR / "harmonyos_mcp_{time}.log"),
        rotation="500 MB",
        retention="10 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        enqueue=True,
    )

    return logger

