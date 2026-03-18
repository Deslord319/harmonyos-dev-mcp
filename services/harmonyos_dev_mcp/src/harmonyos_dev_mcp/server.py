"""HarmonyOS MCP server entry point."""

from loguru import logger

from common.server.base import create_server, run_server

from .config import Config
from .tools import build, e2e, general, ui  # noqa: F401
from .tools.log.query import logs_query  # noqa: F401


def _setup_logger() -> None:
    from .utils.logger import setup_logger

    setup_logger()


def _on_startup() -> None:
    from .container import get_hdc

    try:
        hdc = get_hdc()
        devices = hdc.list_devices()
        logger.info(f"Detected {len(devices)} device(s)")
    except Exception as exc:
        logger.warning(f"Device detection failed: {exc}")


mcp = create_server("harmonyos-tools")


def main() -> None:
    run_server(
        mcp,
        config_class=Config,
        setup_logger_func=_setup_logger,
        on_startup=_on_startup,
    )


if __name__ == "__main__":
    main()
