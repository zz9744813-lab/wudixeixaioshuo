from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.foreshadow import (
    ForeshadowCreate,
    ForeshadowListResponse,
    ForeshadowOut,
    ForeshadowUpdate,
)
from app.services.foreshadow_service import (
    create_foreshadow,
    delete_foreshadow,
    get_foreshadow,
    list_foreshadows,
    update_foreshadow,
)

router = APIRouter()


@router.get("/projects/{project_id}/foreshadows", response_model=ForeshadowListResponse)
async def list_foreshadows(project_id: str, status: str | None = None, db: Session = Depends(get_db)):
    items, total = list_foreshadows(db, project_id, status=status)
    return ForeshadowListResponse(
        items=[
            ForeshadowOut(
                id=it.id,
                project_id=it.project_id,
                chapter_id=it.chapter_id,
                type=it.type,
                description=it.description,
                planted_chapter_index=it.planted_chapter_index,
                resolved_chapter_index=it.resolved_chapter_index,
                resolution=it.resolution,
                status=it.status,
                priority=it.priority,
                created_at=it.created_at,
                updated_at=it.updated_at,
            )
            for it in items
        ],
        total=total,
    )


@router.post("/projects/{project_id}/foreshadows", response_model=ForeshadowOut, status_code=201)
async def create_foreshadow_endpoint(project_id: str, payload: ForeshadowCreate, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_unset=True)
    data["project_id"] = project_id
    item = create_foreshadow(db, data)
    return ForeshadowOut(
        id=item.id,
        project_id=item.project_id,
        chapter_id=item.chapter_id,
        type=item.type,
        description=item.description,
        planted_chapter_index=item.planted_chapter_index,
        resolved_chapter_index=item.resolved_chapter_index,
        resolution=item.resolution,
        status=item.status,
        priority=item.priority,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.put("/projects/{project_id}/foreshadows/{fs_id}", response_model=ForeshadowOut)
async def update_foreshadow_endpoint(project_id: str, fs_id: str, payload: ForeshadowUpdate, db: Session = Depends(get_db)):
    item = update_foreshadow(db, fs_id, payload)
    if not item:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="foreshadow not found")
    return ForeshadowOut(
        id=item.id,
        project_id=item.project_id,
        chapter_id=item.chapter_id,
        type=item.type,
        description=item.description,
        planted_chapter_index=item.planted_chapter_index,
        resolved_chapter_index=item.resolved_chapter_index,
        resolution=item.resolution,
        status=item.status,
        priority=item.priority,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.delete("/projects/{project_id}/foreshadows/{fs_id}")
async def delete_foreshadow_endpoint(project_id: str, fs_id: str, db: Session = Depends(get_db)):
    ok = delete_foreshadow(db, fs_id)
    if not ok:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="foreshadow not found")
    return {"ok": True}
