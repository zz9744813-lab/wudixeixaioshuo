"""
Structured Logging - 结构化日志配置
基于 JSON format，便于日志收集和分析
"""

import json
import logging
import logging.handlers
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from app.config import settings


class JSONFormatter(logging.Formatter):
    """JSON 格式日志处理器"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # 添加上下文字段
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "project_id"):
            log_data["project_id"] = record.project_id

        # 添加异常信息
        if record.exc_info:
            exc_type, exc_value, exc_tb = record.exc_info
            log_data["exception"] = {
                "type": exc_type.__name__ if exc_type else None,
                "message": str(exc_value) if exc_value else None,
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # 添加额外字段
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data, ensure_ascii=False, default=str)


class TextFormatter(logging.Formatter):
    """文本格式日志处理器（用于开发环境）"""

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def format(self, record: logging.LogRecord) -> str:
        # 添加上下文信息
        extra_info = []
        if hasattr(record, "request_id"):
            extra_info.append(f"req={record.request_id}")
        if hasattr(record, "user_id"):
            extra_info.append(f"user={record.user_id}")

        if extra_info:
            record.message = f"{record.getMessage()} | {' | '.join(extra_info)}"

        return super().format(record)


def get_log_level() -> int:
    """获取日志级别"""
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    return level_map.get(settings.LOG_LEVEL.upper(), logging.INFO)


def setup_logging():
    """配置日志系统"""
    # 创建 logs 目录
    log_dir = Path(settings.DATABASE_URL.replace("sqlite:///", "")).parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # 根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(get_log_level())

    # 清除现有处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    is_development = settings.APP_ENV == "development"

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(get_log_level())

    if is_development:
        console_handler.setFormatter(TextFormatter())
    else:
        console_handler.setFormatter(JSONFormatter())

    root_logger.addHandler(console_handler)

    # 文件处理器（按天轮转）
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=log_dir / "app.log",
        when="midnight",
        interval=1,
        backupCount=30,  # 保留30天
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(file_handler)

    # 错误日志单独文件
    error_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "error.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(error_handler)

    # 第三方库日志级别调整
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    logging.info(f"Logging configured (env={settings.APP_ENV}, level={settings.LOG_LEVEL})")


class LoggerAdapter(logging.LoggerAdapter):
    """支持上下文信息的日志适配器"""

    def __init__(
        self,
        logger: logging.Logger,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        project_id: Optional[int] = None,
    ):
        super().__init__(logger, {})
        self.request_id = request_id
        self.user_id = user_id
        self.project_id = project_id

    def process(self, msg, kwargs):
        """处理日志消息"""
        extra = kwargs.get("extra", {})
        extra["request_id"] = self.request_id
        extra["user_id"] = self.user_id
        extra["project_id"] = self.project_id
        kwargs["extra"] = extra
        return msg, kwargs

    def with_context(
        self,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        project_id: Optional[int] = None,
    ) -> "LoggerAdapter":
        """创建带有新上下文的日志器"""
        return LoggerAdapter(
            self.logger,
            request_id=request_id or self.request_id,
            user_id=user_id or self.user_id,
            project_id=project_id or self.project_id,
        )

    def log_operation(
        self,
        operation: str,
        entity_type: str,
        entity_id: Optional[Any] = None,
        details: Optional[Dict] = None,
        level: str = "INFO",
    ):
        """记录操作日志"""
        extra_fields = {
            "operation": operation,
            "entity_type": entity_type,
            "entity_id": str(entity_id) if entity_id else None,
            "details": details or {},
        }

        method = getattr(self, level.lower(), self.info)
        method(f"{operation} {entity_type}", extra={"extra_fields": extra_fields})


def get_logger(name: str) -> LoggerAdapter:
    """获取带适配器的日志器"""
    return LoggerAdapter(logging.getLogger(name))


# 专用日志器
app_logger = get_logger("app")
api_logger = get_logger("app.api")
db_logger = get_logger("app.db")
llm_logger = get_logger("app.llm")
task_logger = get_logger("app.task")
