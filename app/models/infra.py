"""Infrastructure & governance tables (spec §28–§35, EPIC-A).

Prompt Registry, Model Registry, Run provenance, Context Package, Task
state-machine and dead-letter queue. These are the backbone the Agents and
future Workers depend on.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    String,
    Text,
    Integer,
    ForeignKey,
    DateTime,
    Float,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models._mixin import TimestampMixin
from app.models.enums import TaskStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PromptRegistry(TimestampMixin, Base):
    """No prompt is hardcoded in code (禁止12); every prompt is a versioned row (§28)."""

    __tablename__ = "prompt_registry"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    purpose: Mapped[str] = mapped_column(String(256), nullable=False)
    input_schema: Mapped[dict] = mapped_column(JSON, default=dict)
    output_schema: Mapped[dict] = mapped_column(JSON, default=dict)
    model_class: Mapped[str | None] = mapped_column(String(64))
    change_reason: Mapped[str | None] = mapped_column(Text)        # §69: why changed
    benchmark_result: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="active")
    file_path: Mapped[str | None] = mapped_column(String(512))
    content: Mapped[str] = mapped_column(Text, nullable=False)


class ModelRegistry(TimestampMixin, Base):
    """Each model carries capability tags used by the Router (§29)."""

    __tablename__ = "model_registry"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(64))
    capability_tags: Mapped[list] = mapped_column(JSON, default=list)  # reasoning/creative/judge/...
    notes: Mapped[str | None] = mapped_column(Text)


class Run(TimestampMixin, Base):
    """One Agent invocation. Provenance root (§35)."""

    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_type: Mapped[str] = mapped_column(String(128), nullable=False)
    parent_task: Mapped[str | None] = mapped_column(String(64))
    prompt_version: Mapped[str | None] = mapped_column(String(64))
    context_package_id: Mapped[str | None] = mapped_column(String(64))
    idempotency_key: Mapped[str | None] = mapped_column(String(128), unique=True)
    status: Mapped[TaskStatus] = mapped_column(default=TaskStatus.RUNNING, nullable=False)
    input_ref: Mapped[dict] = mapped_column(JSON, default=dict)
    output_ref: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence: Mapped[float | None] = mapped_column(Float)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    uncertainties: Mapped[list] = mapped_column(JSON, default=list)
    started_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    finished_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))


class ModelCall(TimestampMixin, Base):
    """A single LLM call, fully traced (§35)."""

    __tablename__ = "model_calls"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_task: Mapped[str | None] = mapped_column(String(64))
    input_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    output_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    schema_version: Mapped[str] = mapped_column(String(16), default="1.0")
    derived_artifacts: Mapped[list] = mapped_column(JSON, default=list)
    error: Mapped[str | None] = mapped_column(Text)
    called_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ContextPackage(TimestampMixin, Base):
    """Every Agent call is wrapped in a Context Package (§30)."""

    __tablename__ = "context_packages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task: Mapped[str] = mapped_column(String(128), nullable=False)
    source_scene_id: Mapped[str | None] = mapped_column(String(64))
    neighbor_scenes: Mapped[list] = mapped_column(JSON, default=list)
    relevant_character_states: Mapped[list] = mapped_column(JSON, default=list)
    relevant_facts: Mapped[list] = mapped_column(JSON, default=list)
    active_relationships: Mapped[list] = mapped_column(JSON, default=list)
    active_foreshadows: Mapped[list] = mapped_column(JSON, default=list)
    prior_claims: Mapped[list] = mapped_column(JSON, default=list)
    constraints: Mapped[list] = mapped_column(JSON, default=list)
    exclusions: Mapped[list] = mapped_column(JSON, default=list)
    retrieval_results: Mapped[list] = mapped_column(JSON, default=list)
    prompt_version: Mapped[str | None] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class Task(TimestampMixin, Base):
    """Idempotent task record for the future Worker/Queue layer (§33, §40)."""

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    type: Mapped[str] = mapped_column(String(128), nullable=False)
    queue: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[TaskStatus] = mapped_column(default=TaskStatus.PENDING, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), unique=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    retries: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    error: Mapped[str | None] = mapped_column(Text)
    scheduled_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))


class DeadLetter(TimestampMixin, Base):
    """Failed tasks beyond max_retries land here instead of retrying forever (禁止11)."""

    __tablename__ = "dead_letter"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    original_task_id: Mapped[str | None] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text)
    failed_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=_utcnow)
