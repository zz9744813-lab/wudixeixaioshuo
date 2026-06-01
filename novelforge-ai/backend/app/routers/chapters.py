"""NovelForge AI - Chapter stubs"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter()


@router.get("/projects/{project_id}/chapters")
async def list_chapters(project_id: int, db: Session = Depends(get_db)):
    return {"items": [], "total": 0}
