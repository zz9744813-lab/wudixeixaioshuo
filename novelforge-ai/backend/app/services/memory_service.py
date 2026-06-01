from __future__ import annotations

from typing import Any

from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.models.entities import MemoryItem


def list_memory_items(
    db: Session,
    project_id: str,
    *,
    item_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[MemoryItem], int]:
    stmt = select(MemoryItem).where(MemoryItem.project_id == project_id)
    if item_type:
        stmt = stmt.where(MemoryItem.item_type == item_type)
    stmt = stmt.order_by(desc(MemoryItem.created_at)).limit(limit).offset(offset)
    items = list(db.execute(stmt).scalars().all())

    count_stmt = select(MemoryItem).where(MemoryItem.project_id == project_id)
    if item_type:
        count_stmt = count_stmt.where(MemoryItem.item_type == item_type)
    total = db.execute(count_stmt).scalar_one()
    return items, total


def get_memory_item(db: Session, item_id: str) -> MemoryItem | None:
    return db.get(MemoryItem, item_id)


def create_memory_item(db: Session, payload: Any) -> MemoryItem:
    item = MemoryItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_memory_item(
    db: Session, item_id: str, payload: Any
) -> MemoryItem | None:
    item = db.get(MemoryItem, item_id)
    if not item:
        return None
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


def delete_memory_item(db: Session, item_id: str) -> bool:
    item = db.get(MemoryItem, item_id)
    if not item:
        return False
    db.delete(item)
    db.commit()
    return True
