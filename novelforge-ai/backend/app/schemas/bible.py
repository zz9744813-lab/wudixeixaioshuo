from __future__ import annotations

from uuid import UUID
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ProjectBibleUpdate(BaseModel):
    selling_points: str | None = None
    worldview: str | None = None
    protagonist: str | None = None
    characters: list[Any] | None = None
    factions: list[Any] | None = None
    power_system: str | None = None
    plot_rules: str | None = None
    style_guide: str | None = None
    reader_expectation: str | None = None
    forbidden_elements: str | None = None


class ProjectBibleOut(BaseModel):
    id: UUID
    project_id: UUID
    selling_points: str | None
    worldview: str | None
    protagonist: str | None
    characters: list[Any] | None
    factions: list[Any] | None
    power_system: str | None
    plot_rules: str | None
    style_guide: str | None
    reader_expectation: str | None
    forbidden_elements: str | None
    version: int
    created_at: datetime | None
    updated_at: datetime | None
