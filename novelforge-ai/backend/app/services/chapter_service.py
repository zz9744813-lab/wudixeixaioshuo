"""NovelForge AI - Chapter service"""
from __future__ import annotations

from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.entities import Chapter
from app.schemas.chapter import ChapterCreate, ChapterUpdate


def list_chapters(db: Session, project_id: str, *, limit: int = 200, offset: int = 0) -> tuple[list[Chapter], int]:
    stmt = (
        select(Chapter)
        .where(Chapter.project_id == project_id)
        .order_by(Chapter.chapter_index)
        .limit(limit)
        .offset(offset)
    )
    items = list(db.execute(stmt).scalars().all())
    total_stmt = select(Chapter).where(Chapter.project_id == project_id).subquery().count()
    total = db.execute(total_stmt).scalar_one()
    return items, total


def get_chapter(db: Session, chapter_id: str) -> Chapter | None:
    return db.get(Chapter, chapter_id)


def create_chapter(db: Session, payload: ChapterCreate) -> Chapter:
    chapter = Chapter(**payload.model_dump())
    db.add(chapter)
    db.commit()
    db.refresh(chapter)
    return chapter


def update_chapter(db: Session, chapter_id: str, payload: ChapterUpdate) -> Chapter | None:
    chapter = db.get(Chapter, chapter_id)
    if not chapter:
        return None
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(chapter, field, value)
    db.commit()
    db.refresh(chapter)
    return chapter


def delete_chapter(db: Session, chapter_id: str) -> bool:
    chapter = db.get(Chapter, chapter_id)
    if not chapter:
        return False
    db.delete(chapter)
    db.commit()
    return True
