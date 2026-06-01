"""NovelForge AI - Structured logger"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path("/app/data/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_LEVEL = "INFO"  # overridden by config in main


def get_logger(name: str) -> logging.Logger:
    """
    Build a loguru-compatible programming interface and add daily rotation
    Write to /app/data/logs/<name>.log. Support console parallel output
    """
    base = logging.getLogger(name)
    base.handlers.clear()
    base.setLevel(LOG_LEVEL)

    fmt = logging.Formatter(
        '{"time":"%(asctime)s","name":"%(name)s","level":"%(levelname)s",'
        '"message":%(message)s}',
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    # console
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(LOG_LEVEL)
    console.setFormatter(fmt)
    base.addHandler(console)

    # file rotation
    file_handler = RotatingFileHandler(
        LOG_DIR / f"{name}.jsonl",
        maxBytes=10 * 1024 * 1024,
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setLevel("DEBUG")
    file_handler.setFormatter(fmt)
    base.addHandler(file_handler)

    return base


def get_logger_factory() -> dict:
    """Map configures internal loguru logger"""
    logging.basicConfig(level=LOG_LEVEL, format="%(message)s", stream=sys.stdout)
    loguru_logger = logging.getLogger("novelforge")
    loguru_logger.setLevel(LOG_LEVEL)
    return {"novelforge": loguru_logger}
