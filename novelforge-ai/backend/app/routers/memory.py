from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.memory import (
    MemoryItemCreate,
    MemoryItemListResponse,
    MemoryItemOut,
    MemoryItemUpdate,
)
from app.services.memory_service import (
    create_memory_item,
    delete_memory_item,
    get_memory_item,
    list_memory_items,
    update_memory_item,
)

router = APIRouter()


@router.get("/projects/{project_id}/memory", response_model=MemoryItemListResponse)
async def list_memory(project_id: str, item_type: str | None = None, db: Session = Depends(get_db)):
    items, total = list_memory_items(db, project_id, item_type=item_type)
    return MemoryItemListResponse(
        items=[
            MemoryItemOut(
                id=it.id,
                project_id=it.project_id,
                chapter_id=it.chapter_id,
                item_type=it.item_type,
                content=it.content,
                embedding=it.embedding,
                tags=it.tags,
                metadata=it.metadata,
                created_at=it.created_at,
                updated_at=it.updated_at,
            )
            for it in items
        ],
        total=total,
    )


@router.post("/projects/{project_id}/memory", response_model=MemoryItemOut, status_code=201)
async def create_memory(project_id: str, payload: MemoryItemCreate, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_unset=True)
    data["project_id"] = project_id
    item = create_memory_item(db, data)
    return MemoryItemOut(
        id=item.id,
        project_id=item.project_id,
        chapter_id=item.chapter_id,
        item_type=item.item_type,
        content=item.content,
        embedding=item.embedding,
        tags=item.tags,
        metadata=item.metadata,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.put("/projects/{project_id}/memory/{item_id}", response_model=MemoryItemOut)
async def update_memory(project_id: str, item_id: str, payload: MemoryItemUpdate, db: Session = Depends(get_db)):
    item = update_memory_item(db, item_id, payload)
    if not item:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="memory item not found")
    return MemoryItemOut(
        id=item.id,
        project_id=item.project_id,
        chapter_id=item.chapter_id,
        item_type=item.item_type,
        content=item.content,
        embedding=item.embedding,
        tags=item.tags,
        metadata=item.metadata,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.delete("/projects/{project_id}/memory/{item_id}")
async def delete_memory(project_id: str, item_id: str, db: Session = Depends(get_db)):
    ok = delete_memory_item(db, item_id)
    if not ok:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="memory item not found")
    return {"ok": True}
