"""NovelForge AI - Export schemas"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ProjectExportInfo(BaseModel):
    id: str
    title: str
    genre: str | None
    description: str | None
    target_total_words: int
    target_chapter_words: int
    daily_word_goal: int


class ChapterExportItem(BaseModel):
    index: int
    title: str
    summary: str | None
    content: str | None
    word_count: int
    status: str


class ExportData(BaseModel):
    project: ProjectExportInfo
    chapters: list[ChapterExportItem]
    exported_at: str
