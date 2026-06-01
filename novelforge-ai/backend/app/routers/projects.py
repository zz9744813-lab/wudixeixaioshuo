from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.project import ProjectCreate, ProjectListResponse, ProjectOut, ProjectUpdate
from app.services.project_service import (
    create_project,
    delete_project,
    get_project,
    list_projects,
    update_project,
)

router = APIRouter()


@router.get("/projects", response_model=ProjectListResponse)
async def list_projects_endpoint(db: Session = Depends(get_db)):
    items, total = list_projects(db)
    return ProjectListResponse(
        items=[
            ProjectOut(
                id=item.id,
                title=item.title,
                genre=item.genre,
                description=item.description,
                target_total_words=item.target_total_words,
                target_chapter_words=item.target_chapter_words,
                daily_word_goal=item.daily_word_goal,
                daily_cost_limit=item.daily_cost_limit,
                status=item.status,
                auto_production_enabled=item.auto_production_enabled,
                current_chapter_index=item.current_chapter_index,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in items
        ],
        total=total,
    )


@router.post("/projects", response_model=ProjectOut, status_code=201)
async def create_project_endpoint(payload: ProjectCreate, db: Session = Depends(get_db)):
    item = create_project(db, payload)
    return ProjectOut(
        id=item.id,
        title=item.title,
        genre=item.genre,
        description=item.description,
        target_total_words=item.target_total_words,
        target_chapter_words=item.target_chapter_words,
        daily_word_goal=item.daily_word_goal,
        daily_cost_limit=item.daily_cost_limit,
        status=item.status,
        auto_production_enabled=item.auto_production_enabled,
        current_chapter_index=item.current_chapter_index,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.get("/projects/{project_id}", response_model=ProjectOut)
async def get_project_endpoint(project_id: str, db: Session = Depends(get_db)):
    item = get_project(db, project_id)
    if not item:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="project not found")
    return ProjectOut(
        id=item.id,
        title=item.title,
        genre=item.genre,
        description=item.description,
        target_total_words=item.target_total_words,
        target_chapter_words=item.target_chapter_words,
        daily_word_goal=item.daily_word_goal,
        daily_cost_limit=item.daily_cost_limit,
        status=item.status,
        auto_production_enabled=item.auto_production_enabled,
        current_chapter_index=item.current_chapter_index,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.put("/projects/{project_id}", response_model=ProjectOut)
async def update_project_endpoint(project_id: str, payload: ProjectUpdate, db: Session = Depends(get_db)):
    item = update_project(db, project_id, payload)
    if not item:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="project not found")
    return ProjectOut(
        id=item.id,
        title=item.title,
        genre=item.genre,
        description=item.description,
        target_total_words=item.target_total_words,
        target_chapter_words=item.target_chapter_words,
        daily_word_goal=item.daily_word_goal,
        daily_cost_limit=item.daily_cost_limit,
        status=item.status,
        auto_production_enabled=item.auto_production_enabled,
        current_chapter_index=item.current_chapter_index,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.delete("/projects/{project_id}")
async def delete_project_endpoint(project_id: str, db: Session = Depends(get_db)):
    ok = delete_project(db, project_id)
    if not ok:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="project not found")
    return {"ok": True}
