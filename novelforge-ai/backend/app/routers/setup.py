import inspect

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.redis import get_redis
from app.routers.health import router as health_router

router = APIRouter()


CHECK_FNS: list[dict] = []


def register_check(key: str, label: str, fn):
    CHECK_FNS.append({"key": key, "label": label, "fn": fn})


async def _check_database(db: Session):
    try:
        db.execute("SELECT 1")
        return "ok", "PostgreSQL 已连接"
    except Exception as exc:  # pragma: no cover
        return "error", f"PostgreSQL 连接失败: {exc}"


async def _check_redis():
    try:
        r = await get_redis()
        await r.ping()
        await r.aclose()
        return "ok", "Redis 已连接"
    except Exception as exc:  # pragma: no cover
        return "error", f"Redis 连接失败: {exc}"


async def _check_model_provider():
    # Placeholder – real check moved to later phases.
    return "warning", "尚未配置模型 Provider"


async def _check_worker():
    # No worker in P0.
    return "warning", "Worker 尚未启动 (P0 不包含调度器)"


register_check("database", "数据库", _check_database)
register_check("redis", "Redis", _check_redis)
register_check("model_provider", "模型 Provider", _check_model_provider)
register_check("worker", "Worker", _check_worker)


@router.get("/setup/status")
async def setup_status(db: Session = Depends(get_db)):
    checks = []
    next_action = None
    any_error = False

    for item in CHECK_FNS:
        result = item["fn"]
        if inspect.iscoroutinefunction(result):
            status, message = await result(db) if item["key"] == "database" else await result()
        else:
            status, message = result(db) if "db" in inspect.signature(result).parameters else result()

        checks.append(
            {
                "key": item["key"],
                "label": item["label"],
                "status": status,
                "message": message,
            }
        )
        if status == "error":
            any_error = True
        elif status == "warning" and next_action is None:
            next_action = {"type": item["key"], "label": f"配置{item['label']}"}

    if next_action is None and all(c["status"] == "ok" for c in checks):
        next_action = {"type": "enter", "label": "进入生产舱"}

    return {
        "ok": not any_error and all(c["status"] == "ok" for c in checks),
        "checks": checks,
        **({"next_action": next_action} if next_action else {}),
    }
