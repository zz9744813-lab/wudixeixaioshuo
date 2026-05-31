"""Health Router - 健康检查路由"""

from datetime import datetime
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends

from app.database import get_db, engine
from app.schemas import HealthCheck
from app.services.llm_router import get_llm_router
from app.services.worker_service import worker
from sqlalchemy import text, inspect

router = APIRouter()


@router.get("/", response_model=HealthCheck)
async def health_check(db: Session = Depends(get_db)):
    """健康检查端点"""
    try:
        # 测试数据库连接 - SQLAlchemy 2.x
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return HealthCheck(
        status="healthy" if db_status == "connected" else "unhealthy",
        service="24小时小说 Agent 工作台",
        version="0.1.0",
        database=db_status,
    )


@router.get("/runtime")
async def health_runtime(db: Session = Depends(get_db)):
    """运行时诊断——包含数据库、Worker、LLM路由、模型服务等"""
    # 数据库
    db_ok = True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        db_ok = False

    # Worker
    try:
        ws = worker.get_status()
        worker_status = ws.get("status", "unknown")
    except Exception:
        worker_status = "error"

    # LLM 路由
    router_ok = True
    try:
        db_router = get_llm_router(db)
        audit = db_router.audit_role_coverage()
        router_ok = audit.get("ok", False)
    except Exception:
        router_ok = False

    # 模型 provider 数量
    from app.models.model_config import ModelProvider
    provider_count = 0
    try:
        provider_count = db.query(ModelProvider).count()
    except Exception:
        pass

    return {
        "service": "backend",
        "version": "0.1.0",
        "env": __import__("app.config").config.settings.APP_ENV,
        "database_url_masked": "sqlite:///..." if db_ok else "disconnected",
        "db_ok": db_ok,
        "time": datetime.utcnow().isoformat(),
        "worker_status": worker_status,
        "llm_router_ok": router_ok,
        "provider_count": provider_count,
        "pending_tasks": ws.get("pending_tasks", 0) if isinstance(ws, dict) else 0,
    }
