import importlib
from pathlib import Path


def test_logger_uses_localappdata_directory(monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", r"D:\Users\tester\AppData\Local")

    import common.utils.logger as logger_module

    logger_module = importlib.reload(logger_module)

    assert logger_module._resolve_log_dir() == Path(r"D:\Users\tester\AppData\Local\harmonyos-dev-mcp\logs")
    assert logger_module._LOG_DIR == Path(r"D:\Users\tester\AppData\Local\harmonyos-dev-mcp\logs")
