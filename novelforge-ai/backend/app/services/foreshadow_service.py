from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Foreshadow


def list_foreshadows(
    db: Session,
    project_id: str,
    *,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[Foreshadow], int]:
    stmt = select(Foreshadow).where(Foreshadow.project_id == project_id)
    if status:
        stmt = stmt.where(Foreshadow.status == status)
    stmt = (
        stmt.order_by(Foreshadow.priority.desc())
        .limit(limit)
        .offset(offset)
    )
    items = list(db.execute(stmt).scalars().all())

    count_stmt = select(Foreshadow).where(Foreshadow.project_id == project_id)
    if status:
        count_stmt = count_stmt.where(Foreshadow.status == status)
    total = db.execute(count_stmt).scalar_one()
    return items, total


def get_foreshadow(db: Session, fs_id: str) -> Foreshadow | None:
    return db.get(Foreshadow, fs_id)


def create_foreshadow(db: Session, payload: Any) -> Foreshadow:
    fs = Foreshadow(**payload.model_dump())
    db.add(fs)
    db.commit()
    db.refresh(fs)
    return fs


def update_foreshadow(
    db: Session, fs_id: str, payload: Any
) -> Foreshadow | None:
    fs = db.get(Foreshadow, fs_id)
    if not fs:
        return None
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(fs, field, value)
    db.commit()
    db.refresh(fs)
    return fs


def delete_foreshadow(db: Session, fs_id: str) -> bool:
    fs = db.get(Foreshadow, fs_id)
    if not fs:
        return False
    db.delete(fs)
    db.commit()
    return True
