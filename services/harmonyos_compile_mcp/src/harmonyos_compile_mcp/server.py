"""HarmonyOS compile MCP server entry point."""

from common.utils.logger import setup_logger
from common.server.base import create_server, run_server

from .config import Config
from .tools import compile_tools  # noqa: F401


def _setup_logger() -> None:
    setup_logger(app_name="harmonyos_compile_mcp", log_level=Config.LOG_LEVEL)


mcp = create_server("harmonyos-compile-tools")


def main() -> None:
    run_server(
        mcp,
        config_class=Config,
        setup_logger_func=_setup_logger,
    )


if __name__ == "__main__":
    main()
