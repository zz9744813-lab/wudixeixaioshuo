"""Export API: Obsidian console (spec §42)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.export.obsidian import export_vault

router = APIRouter(prefix="/api/v1/export", tags=["export"])


@router.post("/obsidian")
def export_obsidian(db: Session = Depends(get_db)):
    return export_vault(db)
