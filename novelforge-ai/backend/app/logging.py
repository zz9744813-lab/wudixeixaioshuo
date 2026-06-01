"""NovelForge AI - Structured logger"""

import json
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict

LOG_DIR = Path("/app/data/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def _build_handler(stream: Any, level: int = logging.INFO) -> logging.Handler:
    handler = logging.StreamHandler(stream) if stream else RotatingFileHandler(
        LOG_DIR / "novelforge.jsonl", maxBytes=10 * 1024 * 1024, backupCount=7, encoding="utf-8"
    )
    handler.setLevel(level)
    handler.setFormatter(JsonFormatter())
    return handler


def get_logger(name: str = "novelforge") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.addHandler(_build_handler(sys.stdout))
        logger.setLevel(logging.INFO)
    return logger
