from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import ProjectBible


def get_project_bible(db: Session, project_id: str) -> ProjectBible | None:
    stmt = select(ProjectBible).where(ProjectBible.project_id == project_id)
    return db.execute(stmt).scalar_one_or_none()


def get_or_create_bible(db: Session, project_id: str) -> tuple[ProjectBible, bool]:
    """Get or create bible for a project. Returns (bible, created_bool)."""
    existing = get_project_bible(db, project_id)
    if existing:
        return existing, False
    bible = ProjectBible(project_id=project_id)
    db.add(bible)
    db.commit()
    db.refresh(bible)
    return bible, True


def update_project_bible(
    db: Session, project_id: str, payload: Any
) -> ProjectBible | None:
    """Update project bible fields (payload is a Pydantic model with .model_dump(exclude_unset=True))."""
    bible = get_project_bible(db, project_id)
    if not bible:
        return None
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(bible, field, value)
    db.commit()
    db.refresh(bible)
    return bible
