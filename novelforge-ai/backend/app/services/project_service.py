"""NovelForge AI - Project service"""
from __future__ import annotations

from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.entities import Project
from app.schemas.project import ProjectCreate, ProjectUpdate


def list_projects(db: Session, *, limit: int = 50, offset: int = 0) -> tuple[list[Project], int]:
    stmt = select(Project).order_by(desc(Project.created_at)).limit(limit).offset(offset)
    items = list(db.execute(stmt).scalars().all())
    total = db.execute(select(Project).subquery().count()).scalar_one()
    return items, total


def get_project(db: Session, project_id: str) -> Project | None:
    return db.get(Project, project_id)


def create_project(db: Session, payload: ProjectCreate) -> Project:
    project = Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def update_project(db: Session, project_id: str, payload: ProjectUpdate) -> Project | None:
    project = db.get(Project, project_id)
    if not project:
        return None
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project_id: str) -> bool:
    project = db.get(Project, project_id)
    if not project:
        return False
    db.delete(project)
    db.commit()
    return True
