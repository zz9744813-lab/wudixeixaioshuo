from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.chapter import ChapterCreate, ChapterListResponse, ChapterOut, ChapterUpdate
from app.services.chapter_service import (
    create_chapter,
    delete_chapter,
    get_chapter,
    list_chapters,
    update_chapter,
)

router = APIRouter()


@router.get("/projects/{project_id}/chapters", response_model=ChapterListResponse)
async def list_chapters_endpoint(project_id: str, db: Session = Depends(get_db)):
    items, total = list_chapters(db, project_id)
    return ChapterListResponse(
        items=[
            ChapterOut(
                id=item.id,
                project_id=item.project_id,
                chapter_index=item.chapter_index,
                title=item.title,
                summary=item.summary,
                content=item.content,
                word_count=item.word_count,
                status=item.status,
                quality_score=item.quality_score,
                continuity_score=item.continuity_score,
                locked=item.locked,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in items
        ],
        total=total,
    )


@router.post("/projects/{project_id}/chapters", response_model=ChapterOut, status_code=201)
async def create_chapter_endpoint(project_id: str, payload: ChapterCreate, db: Session = Depends(get_db)):
    item = create_chapter(db, payload)
    return ChapterOut(
        id=item.id,
        project_id=item.project_id,
        chapter_index=item.chapter_index,
        title=item.title,
        summary=item.summary,
        content=item.content,
        word_count=item.word_count,
        status=item.status,
        quality_score=item.quality_score,
        continuity_score=item.continuity_score,
        locked=item.locked,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.get("/projects/{project_id}/chapters/{chapter_id}", response_model=ChapterOut)
async def get_chapter_endpoint(project_id: str, chapter_id: str, db: Session = Depends(get_db)):
    item = get_chapter(db, chapter_id)
    if not item:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="chapter not found")
    return ChapterOut(
        id=item.id,
        project_id=item.project_id,
        chapter_index=item.chapter_index,
        title=item.title,
        summary=item.summary,
        content=item.content,
        word_count=item.word_count,
        status=item.status,
        quality_score=item.quality_score,
        continuity_score=item.continuity_score,
        locked=item.locked,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.put("/projects/{project_id}/chapters/{chapter_id}", response_model=ChapterOut)
async def update_chapter_endpoint(project_id: str, chapter_id: str, payload: ChapterUpdate, db: Session = Depends(get_db)):
    item = update_chapter(db, chapter_id, payload)
    if not item:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="chapter not found")
    return ChapterOut(
        id=item.id,
        project_id=item.project_id,
        chapter_index=item.chapter_index,
        title=item.title,
        summary=item.summary,
        content=item.content,
        word_count=item.word_count,
        status=item.status,
        quality_score=item.quality_score,
        continuity_score=item.continuity_score,
        locked=item.locked,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.delete("/projects/{project_id}/chapters/{chapter_id}")
async def delete_chapter_endpoint(project_id: str, chapter_id: str, db: Session = Depends(get_db)):
    ok = delete_chapter(db, chapter_id)
    if not ok:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="chapter not found")
    return {"ok": True}
