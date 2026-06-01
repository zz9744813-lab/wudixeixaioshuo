import datetime

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.redis import get_redis

router = APIRouter()


async def _check(component: str, probe):
    try:
        return {"component": component, "status": "ok"}
    except Exception as exc:
        return {"component": component, "status": "error", "message": str(exc)}


@router.get("/diagnostics")
async def diagnostics(db: Session = Depends(get_db)):
    backend_start = datetime.datetime.now(datetime.timezone.utc)
    backend_status = "ok"

    # Database
    try:
        db.execute(text("SELECT 1"))
        database_status = {"status": "ok"}
    except Exception as exc:
        database_status = {"status": "error", "message": str(exc)}

    # Redis
    try:
        r = await get_redis()
        await r.ping()
        await r.aclose()
        redis_status = {"status": "ok"}
    except Exception as exc:
        redis_status = {"status": "error", "message": str(exc)}

    backend_elapsed = (datetime.datetime.now(datetime.timezone.utc) - backend_start).total_seconds()

    return {
        "backend": backend_status,
        "backend_elapsed_ms": int(backend_elapsed * 1000),
        "database": database_status,
        "redis": redis_status,
        "worker": {"status": "unknown_phase_1"},
        "log_path": "/app/data/logs",
        "env": settings.app_env,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
