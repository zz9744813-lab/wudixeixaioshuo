from __future__ import annotations

from uuid import UUID
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ForeshadowCreate(BaseModel):
    project_id: UUID | None = None
    chapter_id: UUID | None = None
    type: str = "plot"
    description: str
    planted_chapter_index: int
    priority: int = 0


class ForeshadowUpdate(BaseModel):
    type: str | None = None
    description: str | None = None
    planted_chapter_index: int | None = None
    resolved_chapter_index: int | None = None
    resolution: str | None = None
    status: str | None = None
    priority: int | None = None


class ForeshadowOut(BaseModel):
    id: UUID
    project_id: UUID
    chapter_id: UUID | None
    type: str
    description: str
    planted_chapter_index: int
    resolved_chapter_index: int | None
    resolution: str | None
    status: str
    priority: int
    created_at: datetime | None
    updated_at: datetime | None


class ForeshadowListResponse(BaseModel):
    items: list[ForeshadowOut]
    total: int
