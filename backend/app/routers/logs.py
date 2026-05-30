"""
统一日志聚合接口
提供 model_call / production / evolution 三类日志的统一查询与统计。
"""
from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps.auth import require_api_key
from app.models.model_config import ModelCallLog
from app.models.production import ProductionLog
from app.models.evolution import EvolutionLog

router = APIRouter(prefix="/api/logs", tags=["logs"])


def _level_filter(query, level: Optional[str]):
    if not level:
        return query
    if level == "failed":
        return query.filter(
            or_(
                ModelCallLog.status == "failed",
                ModelCallLog.status == "timeout",
            )
        )
    if level == "timeout":
        return query.filter(ModelCallLog.status == "timeout")
    if level == "success":
        return query.filter(ModelCallLog.status == "success")
    if level == "info":
        return query.filter(ModelCallLog.status == "info")
    if level == "warning":
        return query.filter(ModelCallLog.status == "warning")
    if level == "error":
        return query.filter(ModelCallLog.status == "error")
    return query


def _to_model_call(r) -> dict:
    return {
        "id": r.id,
        "ts": r.created_at.isoformat() if r.created_at else None,
        "type": "model_call",
        "level": r.status or "info",
        "source": f"{r.role}·{r.model_name}",
        "message": r.error_message or r.response_summary or r.request_type,
        "duration_ms": r.duration_ms,
        "tokens": r.total_tokens,
        "cost": r.estimated_cost,
        "project_id": r.project_id,
        "detail": {
            "prompt_summary": r.prompt_summary,
            "response_summary": r.response_summary,
            "input_tokens": r.input_tokens,
            "output_tokens": r.output_tokens,
            "provider_id": r.provider_id,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "error_message": r.error_message,
        },
    }


def _to_production(r) -> dict:
    return {
        "id": r.id,
        "ts": r.created_at.isoformat() if r.created_at else None,
        "type": "production",
        "level": r.log_type,
        "source": f"生产·{r.log_type}",
        "message": r.message,
        "duration_ms": None,
        "tokens": r.tokens_used,
        "cost": r.cost,
        "project_id": r.project_id,
        "detail": {
            "words_written": r.words_written,
            "chapter_id": r.chapter_id,
            "task_id": r.task_id,
            "details": r.details,
        },
    }


def _to_evolution(r) -> dict:
    return {
        "id": r.id,
        "ts": r.created_at.isoformat() if r.created_at else None,
        "type": "evolution",
        "level": r.log_type or "info",
        "source": f"进化·{r.evolution_run_id}",
        "message": r.message,
        "duration_ms": None,
        "tokens": None,
        "cost": None,
        "project_id": None,
        "detail": {
            "evolution_run_id": r.evolution_run_id,
            "details": r.details,
        },
    }


@router.get("", dependencies=[Depends(require_api_key)])
async def list_logs(
    db: Session = Depends(get_db),
    type: str = Query("model_call", enum=["model_call", "production", "evolution", "all"]),
    level: Optional[str] = Query(None, enum=["success", "failed", "timeout", "info", "warning", "error"]),
    project_id: Optional[int] = None,
    q: Optional[str] = None,
    since: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
):
    """统一日志查询"""
    rows = []
    total = 0

    if type in ("model_call", "all"):
        qry = db.query(ModelCallLog).order_by(ModelCallLog.created_at.desc())
        if level:
            if level == "failed":
                qry = qry.filter(ModelCallLog.status.in_(["failed", "timeout"]))
            elif level == "timeout":
                qry = qry.filter(ModelCallLog.status == "timeout")
            else:
                qry = qry.filter(ModelCallLog.status == level)
        if project_id is not None:
            qry = qry.filter(ModelCallLog.project_id == project_id)
        if since:
            qry = qry.filter(ModelCallLog.created_at >= since)
        if q:
            qry = qry.filter(
                or_(
                    ModelCallLog.error_message.ilike(f"%{q}%"),
                    ModelCallLog.response_summary.ilike(f"%{q}%"),
                    ModelCallLog.request_type.ilike(f"%{q}%"),
                )
            )
        total += qry.count()
        mc_rows = qry.limit(limit).offset(offset).all()
        rows.extend([_to_model_call(r) for r in mc_rows])

    # 这里的 production / evolution 在 "all" 模式下会重复翻页，所以生产环境更应拆分。
    # 为简化且避免主键冲突，当前只做(type == production)或(type == evolution)。
    if type == "production":
        qry = db.query(ProductionLog).order_by(ProductionLog.created_at.desc())
        if project_id is not None:
            qry = qry.filter(ProductionLog.project_id == project_id)
        if since:
            qry = qry.filter(ProductionLog.created_at >= since)
        if q:
            qry = qry.filter(
                or_(
                    ProductionLog.message.ilike(f"%{q}%"),
                    ProductionLog.log_type.ilike(f"%{q}%"),
                )
            )
        pr_rows = qry.limit(limit).offset(offset).all()
        rows.extend([_to_production(r) for r in pr_rows])
        total = qry.count()

    if type == "evolution":
        qry = db.query(EvolutionLog).order_by(EvolutionLog.created_at.desc())
        if since:
            qry = qry.filter(EvolutionLog.created_at >= since)
        if q:
            qry = qry.filter(
                or_(
                    EvolutionLog.message.ilike(f"%{q}%"),
                    EvolutionLog.log_type.ilike(f"%{q}%"),
                )
            )
        ev_rows = qry.limit(limit).offset(offset).all()
        rows.extend([_to_evolution(r) for r in ev_rows])
        total = qry.count()

    rows.sort(key=lambda x: x.get("ts") or "", reverse=True)
    rows = rows[:limit]

    return {
        "total": total,
        "items": rows,
        "limit": limit,
        "offset": offset,
    }


@router.get("/stats", dependencies=[Depends(require_api_key)])
async def log_stats(db: Session = Depends(get_db), since: Optional[str] = None):
    """今日概览数据（SQLite 方言）"""
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

    today_counts = db.query(
        func.count(ModelCallLog.id).label("cnt"),
        func.count(ModelCallLog.id).filter(ModelCallLog.status.in_(["failed", "timeout"])).label("fail_cnt"),
        func.avg(ModelCallLog.duration_ms).label("avg_ms"),
        func.coalesce(func.sum(ModelCallLog.total_tokens), 0).label("tokens"),
        func.coalesce(func.sum(ModelCallLog.estimated_cost), 0).label("cost"),
    ).filter(ModelCallLog.created_at >= today_start)

    if since:
        today_counts = today_counts.filter(ModelCallLog.created_at >= since)

    row = today_counts.one_or_none()

    total = row.cnt if row and row.cnt is not None else 0
    fail = row.fail_cnt if row and row.fail_cnt is not None else 0
    avg_ms = round(row.avg_ms, 2) if row and row.avg_ms is not None else 0
    tokens = row.tokens if row and row.tokens is not None else 0
    cost = round(row.cost, 4) if row and row.cost is not None else 0.0

    return {
        "today_calls": total,
        "today_failures": fail,
        "failure_rate": round(fail / total, 4) if total else 0.0,
        "avg_duration_ms": avg_ms,
        "total_tokens": tokens,
        "total_cost": cost,
    }
