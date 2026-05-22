"""Centralised logging configuration for both the FastAPI process and the Celery worker.

Call ``configure_logging()`` once at process startup. All loggers created with
``logging.getLogger(__name__)`` across the codebase will then emit structured
lines to stdout in the format:

    2026-05-22T10:30:45 [INFO ] app.agents.crawler_agent | Crawler persisted 5 pages for audit 3
"""

import logging
import sys


class _LevelPad(logging.Formatter):
    """Formatter that left-pads the level name to 8 chars so columns line up."""

    def format(self, record: logging.LogRecord) -> str:
        record.levelname = record.levelname.ljust(8)
        return super().format(record)


def configure_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO

    fmt = "%(asctime)s [%(levelname)s] %(name)s | %(message)s"
    datefmt = "%Y-%m-%dT%H:%M:%S"
    formatter = _LevelPad(fmt=fmt, datefmt=datefmt)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    # Remove any handlers added by third-party code before us (e.g. basicConfig).
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Silence chatty libraries that aren't useful at INFO.
    _quiet = [
        "httpx", "httpcore", "urllib3", "apify_client",
        "apify", "playwright", "websockets", "asyncio",
        "hpack", "h2",
    ]
    for name in _quiet:
        logging.getLogger(name).setLevel(logging.WARNING)
