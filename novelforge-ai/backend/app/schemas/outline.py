from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class OutlineNodeCreate(BaseModel):
    parent_id: str | None = None
    node_type: str = "chapter"
    order_index: int = 0
    title: str
    summary: str | None = None
    target_words: int | None = None
    node_meta: dict[str, Any] | None = None



class OutlineNodeUpdate(BaseModel):
    parent_id: str | None = None
    node_type: str | None = None
    order_index: int | None = None
    title: str | None = None
    summary: str | None = None
    target_words: int | None = None
    node_meta: dict[str, Any] | None = None



class OutlineNodeOut(BaseModel):
    id: str
    project_id: str
    parent_id: str | None
    node_type: str
    order_index: int
    title: str
    summary: str | None
    target_words: int | None
    node_meta: dict[str, Any] | None
    created_at: datetime | None
    updated_at: datetime | None
