"""NovelForge AI - Project schemas"""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    title: str
    genre: str | None = None
    description: str | None = None
    target_total_words: int = 1_000_000
    target_chapter_words: int = 3_000
    daily_word_goal: int = 10_000
    daily_cost_limit: float = 5.0
    status: str = "draft"
    auto_production_enabled: bool = False


class ProjectUpdate(BaseModel):
    title: str | None = None
    genre: str | None = None
    description: str | None = None
    target_total_words: int | None = None
    target_chapter_words: int | None = None
    daily_word_goal: int | None = None
    daily_cost_limit: float | None = None
    status: str | None = None
    auto_production_enabled: bool | None = None
    current_chapter_index: int | None = None


class ProjectOut(BaseModel):
    id: UUID
    title: str
    genre: str | None
    description: str | None
    target_total_words: int
    target_chapter_words: int
    daily_word_goal: int
    daily_cost_limit: float
    status: str
    auto_production_enabled: bool
    current_chapter_index: int
    created_at: datetime | None
    updated_at: datetime | None


class ProjectListResponse(BaseModel):
    items: list[ProjectOut]
    total: int
