"""NovelForge AI - Setup service"""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.entities import ModelProvider


def _check_database(db: Session) -> tuple[str, str]:
    try:
        db.execute(select(1))
        return "ok", "PostgreSQL 已连接"
    except Exception as exc:
        return "error", f"PostgreSQL 连接失败: {exc}"


def _check_redis() -> tuple[str, str]:
    # Redis connectivity is validated in the diagnostics endpoint directly;
    # setup status only reports whether REDIS_URL is configured.
    if not settings.redis_url:
        return "warning", "Redis URL 未配置"
    return "ok", "Redis 已配置"


def _check_model_provider(db: Session) -> tuple[str, str]:
    try:
        count = db.execute(select(func.count(ModelProvider.id))).scalar_one()
        if count == 0:
            return "warning", "尚未配置模型 Provider"
        return "ok", f"已配置 {count} 个模型 Provider"
    except Exception:
        return "error", "模型 Provider 查询失败"


def _check_worker() -> tuple[str, str]:
    return "warning", "Worker 尚未启动 (P1 不包含调度器)"


CHECKS = [
    ("database", "数据库", _check_database),
    ("redis", "Redis", _check_redis),
    ("model_provider", "模型 Provider", _check_model_provider),
    ("worker", "Worker", _check_worker),
]


def compute_setup_status(db: Session) -> dict[str, Any]:
    checks = []
    any_error = False
    next_action: dict | None = None

    for key, label, fn in CHECKS:
        status, message = fn(db) if key in {"database", "model_provider"} else fn()
        checks.append({"key": key, "label": label, "status": status, "message": message})
        if status == "error":
            any_error = True
        elif status == "warning" and next_action is None:
            next_action = {"type": key, "label": f"配置{label}"}

    if next_action is None and not any_error:
        next_action = {"type": "enter", "label": "进入生产舱"}

    return {
        "ok": not any_error and all(c["status"] == "ok" for c in checks),
        "checks": checks,
        **({"next_action": next_action} if next_action else {}),
    }
