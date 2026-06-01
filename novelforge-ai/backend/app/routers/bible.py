from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.bible import ProjectBibleOut, ProjectBibleUpdate
from app.services.bible_service import get_or_create_bible, update_project_bible

router = APIRouter()


@router.get("/projects/{project_id}/bible", response_model=ProjectBibleOut)
async def get_bible(project_id: str, db: Session = Depends(get_db)):
    bible, _ = get_or_create_bible(db, project_id)
    return ProjectBibleOut(
        id=bible.id,
        project_id=bible.project_id,
        selling_points=bible.selling_points,
        worldview=bible.worldview,
        protagonist=bible.protagonist,
        characters=bible.characters,
        factions=bible.factions,
        power_system=bible.power_system,
        plot_rules=bible.plot_rules,
        style_guide=bible.style_guide,
        reader_expectation=bible.reader_expectation,
        forbidden_elements=bible.forbidden_elements,
        version=bible.version,
        created_at=bible.created_at,
        updated_at=bible.updated_at,
    )


@router.patch("/projects/{project_id}/bible", response_model=ProjectBibleOut)
async def patch_bible(project_id: str, payload: ProjectBibleUpdate, db: Session = Depends(get_db)):
    bible = update_project_bible(db, project_id, payload)
    if not bible:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="project not found")
    return ProjectBibleOut(
        id=bible.id,
        project_id=bible.project_id,
        selling_points=bible.selling_points,
        worldview=bible.worldview,
        protagonist=bible.protagonist,
        characters=bible.characters,
        factions=bible.factions,
        power_system=bible.power_system,
        plot_rules=bible.plot_rules,
        style_guide=bible.style_guide,
        reader_expectation=bible.reader_expectation,
        forbidden_elements=bible.forbidden_elements,
        version=bible.version,
        created_at=bible.created_at,
        updated_at=bible.updated_at,
    )
