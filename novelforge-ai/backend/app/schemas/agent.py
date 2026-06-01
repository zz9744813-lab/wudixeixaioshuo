"""NovelForge AI - Agent run schemas"""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class AgentStepOut(BaseModel):
    id: UUID
    agent_name: str
    status: str
    model_name: str | None
    input_tokens: int
    output_tokens: int
    cost: float
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None


class AgentRunCreate(BaseModel):
    project_id: UUID
    chapter_id: UUID | None = None
    chapter_index: int | None = None


class AgentRunOut(BaseModel):
    id: UUID
    project_id: UUID
    chapter_index: int
    status: str
    current_step: str | None
    total_steps: int
    final_score: float | None
    word_count: int
    total_tokens: int
    total_cost: float
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    steps: list[AgentStepOut] | None = None


class AgentRunListResponse(BaseModel):
    items: list[AgentRunOut]
    total: int
