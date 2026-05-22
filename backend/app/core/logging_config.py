"""
Centralised logging utility.

All modules should use:
    from utils.logger import get_logger
    logger = get_logger(__name__)

Logs are written to both stdout and a global log.log file.
"""

import logging
import sys
from typing import Optional

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _build_stream_handler() -> logging.StreamHandler:
    """Create a stream handler for stdout logging."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    return handler


def get_logger(name: Optional[str] = None) -> logging.Logger:
    logger = logging.getLogger(name or "outsource_ai")
    if not logger.handlers:
        logger.addHandler(_build_stream_handler())
    logger.setLevel(getattr(logging, "INFO", logging.DEBUG))
    logger.propagate = False
    return logger
