"""Conflict system (spec §75) and causal graph edges (spec §13)."""
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
from app.models.enums import ConflictType, CausalEdgeType


class Conflict(TimestampMixin, Base):
    __tablename__ = "conflicts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    book_id: Mapped[str] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    scene_id: Mapped[str | None] = mapped_column(ForeignKey("scenes.id", ondelete="SET NULL"))
    parties: Mapped[list] = mapped_column(JSON, default=list)
    object: Mapped[str | None] = mapped_column(String(256))
    type: Mapped[ConflictType] = mapped_column(default=ConflictType.INTERPERSONAL, nullable=False)
    stakes: Mapped[str | None] = mapped_column(Text)
    escalation_level: Mapped[int] = mapped_column(default=0)
    asymmetry: Mapped[str | None] = mapped_column(Text)
    possible_resolutions: Mapped[list] = mapped_column(JSON, default=list)
    current_status: Mapped[str | None] = mapped_column(String(64))


class CausalEdge(TimestampMixin, Base):
    """Directed edge in the causal graph (spec §13). Adjacency ≠ causation."""

    __tablename__ = "causal_edges"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    book_id: Mapped[str] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    from_id: Mapped[str] = mapped_column(String(64), nullable=False)   # event/state id
    to_id: Mapped[str] = mapped_column(String(64), nullable=False)
    type: Mapped[CausalEdgeType] = mapped_column(nullable=False)
    necessity: Mapped[float] = mapped_column(Float, default=0.0)
    sufficiency: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    alternatives: Mapped[list] = mapped_column(JSON, default=list)
