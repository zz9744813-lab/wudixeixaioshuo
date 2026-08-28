"""Structured logging configuration."""
from __future__ import annotations

import logging
import sys

from app.config import get_settings

_SETTINGS = get_settings()


def configure_logging() -> None:
    level = getattr(logging, _SETTINGS.log_level.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-7s %(name)s | %(message)s")
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
