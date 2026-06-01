"""NovelForge AI - Health"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.errors import ExternalServiceError
from app.redis import get_redis

router = APIRouter()


@router.get("/health")
async def health(db: Session = Depends(get_db)):
    db_ok = False
    try:
        db.execute("SELECT 1")
        db_ok = True
    except Exception:
        pass

    redis_ok = False
    try:
        r = get_redis()
        await r.ping()
        await r.aclose()
        redis_ok = True
    except Exception:
        pass

    if not db_ok or not redis_ok:
        raise ExternalServiceError(
            service="database/redis",
            reason="database or redis is unreachable",
        )

    return {
        "status": "ok",
        "service": "novelforge-api",
        "version": "0.1.0",
        "environment": settings.app_env,
    }
