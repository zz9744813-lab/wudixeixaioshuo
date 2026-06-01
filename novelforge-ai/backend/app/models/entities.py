"""NovelForge AI - SQLAlchemy models"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class UuidMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class User(UuidMixin, TimestampMixin, Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)


class ModelProvider(UuidMixin, TimestampMixin, Base):
    __tablename__ = "model_providers"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(64), nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    api_key_mask: Mapped[str | None] = mapped_column(String(64), nullable=True)
    default_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    last_test_result: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_tested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class ModelRoute(UuidMixin, TimestampMixin, Base):
    __tablename__ = "model_routes"

    role: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    primary_provider_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    primary_model: Mapped[str] = mapped_column(String(255), nullable=False)
    fallback_provider_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    fallback_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    max_cost_per_call: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 6), nullable=True
    )
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Project(UuidMixin, TimestampMixin, Base):
    __tablename__ = "projects"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    genre: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_total_words: Mapped[int] = mapped_column(Integer, default=1_000_000, nullable=False)
    target_chapter_words: Mapped[int] = mapped_column(Integer, default=3_000, nullable=False)
    daily_word_goal: Mapped[int] = mapped_column(Integer, default=10_000, nullable=False)
    daily_cost_limit: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("5.0"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    auto_production_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    current_chapter_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    user_id: Map[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class ProjectBible(UuidMixin, TimestampMixin, Base):
    __tablename__ = "project_bibles"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    selling_points: Mapped[str | None] = mapped_column(Text, nullable=True)
    worldview: Mapped[str | None] = mapped_column(Text, nullable=True)
    protagonist: Mapped[str | None] = mapped_column(Text, nullable=True)
    characters: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    factions: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    power_system: Mapped[str | None] = mapped_column(Text, nullable=True)
    plot_rules: Mapped[str | None] = mapped_column(Text, nullable=True)
    style_guide: Mapped[str | None] = mapped_column(Text, nullable=True)
    reader_expectation: Mapped[str | None] = mapped_column(Text, nullable=True)
    forbidden_elements: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class OutlineNode(UuidMixin, TimestampMixin, Base):
    __tablename__ = "outline_nodes"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    node_type: Mapped[str] = mapped_column(String(32), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_words: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)


class Chapter(UuidMixin, TimestampMixin, Base):
    __tablename__ = "chapters"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    outline_node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    chapter_index: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="planned", nullable=False)
    quality_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    continuity_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ChapterVersion(UuidMixin, TimestampMixin, Base):
    __tablename__ = "chapter_versions"

    chapter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    version_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quality_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    change_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)


class ProductionJob(UuidMixin, TimestampMixin, Base):
    __tablename__ = "production_jobs"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    start_chapter_index: Mapped[int] = mapped_column(Integer, nullable=False)
    target_chapter_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    target_words_per_chapter: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_chapters: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_chapters: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=Decimal("0"), nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentRun(UuidMixin, TimestampMixin, Base):
    __tablename__ = "agent_runs"

    job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    chapter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    chapter_index: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    current_step: Mapped[str | None] = mapped_column(String(64), nullable=True)
    total_steps: Mapped[int] = mapped_column(Integer, default=6, nullable=False)
    final_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    continuity_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=Decimal("0"), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentStep(UuidMixin, TimestampMixin, Base):
    __tablename__ = "agent_steps"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    agent_name: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    provider_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    provider_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    input_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    context_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    raw_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_output: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    score_breakdown: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=Decimal("0"), nullable=False)
    duration_seconds: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 3), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MemoryItem(UuidMixin, TimestampMixin, Base):
    __tablename__ = "memory_items"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    chapter_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    item_type: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(JSONB, nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)


class Foreshadow(UuidMixin, TimestampMixin, Base):
    __tablename__ = "foreshadows"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    chapter_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    planted_chapter_index: Mapped[int] = mapped_column(Integer, nullable=False)
    resolved_chapter_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="planted", nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class UsageRecord(UuidMixin, TimestampMixin, Base):
    __tablename__ = "usage_records"

    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    provider_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    provider_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=Decimal("0"), nullable=False)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)


class SystemLog(UuidMixin, Base):
    __tablename__ = "system_logs"

    level: Mapped[str] = mapped_column(String(16), nullable=False)
    component: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
