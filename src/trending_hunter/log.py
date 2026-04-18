from __future__ import annotations

import logging
import os
import sys

_LOGGER_NAME = "trending_hunter"
_logger: logging.Logger | None = None


def setup_logging() -> logging.Logger:
    global _logger

    logger = logging.getLogger(_LOGGER_NAME)

    level_name = os.environ.get("TH_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S"))
        logger.addHandler(handler)

    _logger = logger
    return logger


def get_logger() -> logging.Logger:
    if _logger is None:
        return setup_logging()
    return _logger
