"""NovelForge AI - Project export"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.export_ import ExportData
from app.services.export_service import get_export_data

router = APIRouter()


@router.get("/projects/{project_id}/export")
async def export_project(project_id: str, db: Session = Depends(get_db)):
    return get_export_data(db, project_id)
