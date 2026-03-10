"""HarmonyOS compile MCP server entry point."""

from common.server.base import create_server, run_server

from .config import Config
from .tools import compile_tools  # noqa: F401


def _setup_logger() -> None:
    from .utils.logger import setup_logger

    setup_logger()


mcp = create_server("harmonyos-compile-tools")


def main() -> None:
    run_server(
        mcp,
        config_class=Config,
        setup_logger_func=_setup_logger,
    )


if __name__ == "__main__":
    main()
