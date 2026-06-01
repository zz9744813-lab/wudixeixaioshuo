"""NovelForge AI - Expenses / usage service"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import UsageRecord


def record_usage(
    db: Session,
    *,
    project_id: str | None,
    run_id: str | None,
    provider_id: str | None,
    provider_name: str | None,
    model_name: str | None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost: float = 0.0,
    category: str | None = None,
) -> UsageRecord:
    record = UsageRecord(
        project_id=project_id,
        run_id=run_id,
        provider_id=provider_id,
        provider_name=provider_name,
        model_name=model_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost=cost,
        category=category,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_project_usage(db: Session, project_id: str, *, days: int = 30) -> list[UsageRecord]:
    cutoff = datetime.now(timezone.utc)
    # Simple placeholder: returns all records; real impl adds date filtering.
    stmt = select(UsageRecord).where(UsageRecord.project_id == project_id).order_by(UsageRecord.created_at.desc())
    return list(db.execute(stmt).scalars().all())
