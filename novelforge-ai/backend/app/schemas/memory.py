from __future__ import annotations

from uuid import UUID
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class MemoryItemCreate(BaseModel):
    project_id: UUID | None = None
    chapter_id: UUID | None = None
    item_type: str
    content: str
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


class MemoryItemUpdate(BaseModel):
    item_type: str | None = None
    content: str | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


class MemoryItemOut(BaseModel):
    id: UUID
    project_id: UUID
    chapter_id: UUID | None
    item_type: str
    content: str
    embedding: list[float] | None
    tags: list[str] | None
    metadata: dict[str, Any] | None
    created_at: datetime | None
    updated_at: datetime | None


class MemoryListResponse(BaseModel):
    items: list[MemoryItemOut]
    total: int
