"""NovelForge AI - Project stubs"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db

router = APIRouter()


class ProjectOut(BaseModel):
    id: int
    title: str
    genre: str | None = None
    current_chapter: int = 0
    total_words: int = 0
    last_produced_at: str | None = None
    status: str = "idle"


@router.get("/projects")
async def list_projects(db: Session = Depends(get_db)):
    # P0 stub – returns empty list until models are added in P1.
    return {"items": [], "total": 0}


@router.get("/projects/{project_id}")
async def get_project(project_id: int, db: Session = Depends(get_db)):
    return ProjectOut(id=project_id, title="未命名项目").model_dump()
