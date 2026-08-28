"""Knowledge State system (spec §10): the linchpin of long-form consistency.

The same Fact can hold a different KnowledgeStatus for A, B, the Reader, etc.
Every acquisition is sourced (spec §10.3).
"""
from __future__ import annotations

from sqlalchemy import (
    ForeignKey,
    JSON,
    String,
    Text,
    Float,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models._mixin import TimestampMixin
from app.models.enums import KnowledgeStatus


class Fact(TimestampMixin, Base):
    __tablename__ = "facts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    book_id: Mapped[str] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(64))
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)


class KnowledgeState(TimestampMixin, Base):
    """Status of a Fact in one character's (or the reader's) mind at a scene."""

    __tablename__ = "knowledge_states"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    fact_id: Mapped[str] = mapped_column(ForeignKey("facts.id", ondelete="CASCADE"), nullable=False)
    character_id: Mapped[str | None] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE")
    )  # NULL = reader/omniscient
    scene_id: Mapped[str] = mapped_column(ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[KnowledgeStatus] = mapped_column(default=KnowledgeStatus.UNKNOWN, nullable=False)
    certainty: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    acquisition_event_id: Mapped[str | None] = mapped_column(String(64))
    evidence: Mapped[list] = mapped_column(JSON, default=list)


class InformationGap(TimestampMixin, Base):
    """Asymmetric knowledge between characters / reader (spec §16 PASS-12, §73)."""

    __tablename__ = "information_gaps"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scene_id: Mapped[str] = mapped_column(ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False)
    fact_id: Mapped[str | None] = mapped_column(ForeignKey("facts.id", ondelete="SET NULL"))
    reader_knows: Mapped[bool] = mapped_column(default=False)
    character_knows: Mapped[list] = mapped_column(JSON, default=list)
    character_does_not_know: Mapped[list] = mapped_column(JSON, default=list)
    description: Mapped[str | None] = mapped_column(Text)


class Foreshadow(TimestampMixin, Base):
    """Foreshadow / promise tracking (spec §73, §74)."""

    __tablename__ = "foreshadows"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    book_id: Mapped[str] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    planted_scene_id: Mapped[str | None] = mapped_column(ForeignKey("scenes.id", ondelete="SET NULL"))
    target_payoff: Mapped[str | None] = mapped_column(String(256))
    visibility: Mapped[str | None] = mapped_column(String(32))
    reader_awareness: Mapped[str | None] = mapped_column(String(32))
    character_awareness: Mapped[list] = mapped_column(JSON, default=list)
    reinforcement_scenes: Mapped[list] = mapped_column(JSON, default=list)
    expected_payoff_window: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="PLANTED")


class Payoff(TimestampMixin, Base):
    __tablename__ = "payoffs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    foreshadow_id: Mapped[str | None] = mapped_column(ForeignKey("foreshadows.id", ondelete="SET NULL"))
    scene_id: Mapped[str | None] = mapped_column(ForeignKey("scenes.id", ondelete="SET NULL"))
    description: Mapped[str | None] = mapped_column(Text)
    quality: Mapped[float] = mapped_column(Float, default=0.0)
