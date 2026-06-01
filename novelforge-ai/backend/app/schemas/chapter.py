"""NovelForge AI - Chapter schemas"""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ChapterCreate(BaseModel):
    project_id: UUID
    chapter_index: int
    title: str
    summary: str | None = None
    target_words: int | None = None


class ChapterUpdate(BaseModel):
    title: str | None = None
    summary: str | None = None
    content: str | None = None
    word_count: int | None = None
    status: str | None = None
    quality_score: float | None = None
    continuity_score: float | None = None
    locked: bool | None = None


class ChapterOut(BaseModel):
    id: UUID
    project_id: UUID
    chapter_index: int
    title: str
    summary: str | None
    content: str | None
    word_count: int
    status: str
    quality_score: float | None
    continuity_score: float | None
    locked: bool
    created_at: datetime | None
    updated_at: datetime | None


class ChapterListResponse(BaseModel):
    items: list[ChapterOut]
    total: int
