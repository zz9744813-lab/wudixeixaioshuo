"""NovelForge AI - Diagnostics service"""
from __future__ import annotations

import datetime
from typing import Any

import redis.asyncio as aioredis
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine


async def _check(component: str, probe):
    try:
        await probe()
        return {"component": component, "status": "ok"}
    except Exception as exc:
        return {"component": component, "status": "error", "message": str(exc)}


async def run_diagnostics(db: Session) -> dict[str, Any]:
    backend_start = datetime.datetime.now(datetime.timezone.utc)
    backend_status = "ok"

    async def db_probe():
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

    async def redis_probe():
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        await r.ping()
        await r.aclose()

    database = await _check("database", db_probe)
    redis = await _check("redis", redis_probe)

    backend_elapsed = (
        datetime.datetime.now(datetime.timezone.utc) - backend_start
    ).total_seconds()

    return {
        "backend": backend_status,
        "backend_elapsed_ms": int(backend_elapsed * 1000),
        "database": database,
        "redis": redis,
        "worker": {"status": "unknown_phase_1"},
        "log_path": "/app/data/logs",
        "env": settings.app_env,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
