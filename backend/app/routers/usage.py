"""
Usage Router - 用量和成本统计 API
"""

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.model_config import ModelCallLog
from app.utils.time_utils import utc_now

router = APIRouter()


@router.get("/summary")
def get_usage_summary(
    project_id: Optional[int] = None,
    days: int = Query(default=7, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """获取用量总览"""
    since = utc_now() - timedelta(days=days)

    query = db.query(ModelCallLog).filter(ModelCallLog.created_at >= since)
    if project_id is not None:
        query = query.filter(ModelCallLog.project_id == project_id)

    total_calls = query.count()
    success_calls = query.filter(ModelCallLog.status == "success").count()
    failed_calls = query.filter(ModelCallLog.status == "failed").count()

    stats = query.with_entities(
        func.sum(ModelCallLog.input_tokens).label("input_tokens"),
        func.sum(ModelCallLog.output_tokens).label("output_tokens"),
        func.sum(ModelCallLog.total_tokens).label("total_tokens"),
        func.sum(ModelCallLog.estimated_cost).label("estimated_cost"),
    ).first()

    return {
        "days": days,
        "total_calls": total_calls,
        "success_calls": success_calls,
        "failed_calls": failed_calls,
        "input_tokens": stats.input_tokens or 0,
        "output_tokens": stats.output_tokens or 0,
        "total_tokens": stats.total_tokens or 0,
        "estimated_cost": round(stats.estimated_cost or 0, 4),
    }


@router.get("/by-role")
def get_usage_by_role(
    project_id: Optional[int] = None,
    days: int = Query(default=7, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """按角色聚合用量"""
    since = utc_now() - timedelta(days=days)

    query = db.query(
        ModelCallLog.role,
        func.count(ModelCallLog.id).label("calls"),
        func.sum(ModelCallLog.total_tokens).label("total_tokens"),
        func.sum(ModelCallLog.estimated_cost).label("estimated_cost"),
    ).filter(
        ModelCallLog.created_at >= since
    )

    if project_id is not None:
        query = query.filter(ModelCallLog.project_id == project_id)

    results = query.group_by(
        ModelCallLog.role
    ).all()

    return [
        {
            "role": r.role,
            "calls": r.calls,
            "total_tokens": r.total_tokens or 0,
            "estimated_cost": round(r.estimated_cost or 0, 4),
        }
        for r in results
    ]


@router.get("/by-model")
def get_usage_by_model(
    project_id: Optional[int] = None,
    days: int = Query(default=7, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """按模型聚合用量"""
    since = utc_now() - timedelta(days=days)

    query = db.query(
        ModelCallLog.model_name,
        func.count(ModelCallLog.id).label("calls"),
        func.sum(ModelCallLog.total_tokens).label("total_tokens"),
        func.sum(ModelCallLog.estimated_cost).label("estimated_cost"),
    ).filter(
        ModelCallLog.created_at >= since
    )

    if project_id is not None:
        query = query.filter(ModelCallLog.project_id == project_id)

    results = query.group_by(
        ModelCallLog.model_name
    ).all()

    return [
        {
            "model_name": r.model_name or "unknown",
            "calls": r.calls,
            "total_tokens": r.total_tokens or 0,
            "estimated_cost": round(r.estimated_cost or 0, 4),
        }
        for r in results
    ]


@router.get("/daily")
def get_daily_usage(
    project_id: Optional[int] = None,
    days: int = Query(default=7, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """按日期趋势"""
    since = utc_now() - timedelta(days=days)

    query = db.query(
        func.date(ModelCallLog.created_at).label("date"),
        func.count(ModelCallLog.id).label("calls"),
        func.sum(ModelCallLog.total_tokens).label("total_tokens"),
        func.sum(ModelCallLog.estimated_cost).label("estimated_cost"),
    ).filter(
        ModelCallLog.created_at >= since
    )

    if project_id is not None:
        query = query.filter(ModelCallLog.project_id == project_id)

    results = query.group_by(
        func.date(ModelCallLog.created_at)
    ).order_by(
        func.date(ModelCallLog.created_at)
    ).all()

    return [
        {
            "date": str(r.date),
            "calls": r.calls,
            "total_tokens": r.total_tokens or 0,
            "estimated_cost": round(r.estimated_cost or 0, 4),
        }
        for r in results
    ]
