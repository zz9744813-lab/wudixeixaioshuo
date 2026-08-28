"""Decomposition Layer (spec §7, §8, §16 PASS-xx): Event, Perception, Belief, Goal.

These are the atomic products of the multi-pass book decomposition. Each is a
Claim-carrying artifact rather than a direct write to canonical state (P-08).
"""
from __future__ import annotations

from sqlalchemy import (
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    Float,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models._mixin import TimestampMixin
from app.models.enums import EventType


class Event(TimestampMixin, Base):
    """A state change (spec §8). Multi-label via `types`."""

    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scene_id: Mapped[str] = mapped_column(
        ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False
    )
    book_id: Mapped[str] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(64))
    types: Mapped[list] = mapped_column(JSON, default=list)  # list[EventType]
    description: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    source_span_id: Mapped[str | None] = mapped_column(String(64))


class Perception(TimestampMixin, Base):
    """What a character perceived in a scene (spec §16 PASS-04)."""

    __tablename__ = "perceptions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scene_id: Mapped[str] = mapped_column(ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False)
    character_id: Mapped[str] = mapped_column(ForeignKey("characters.id", ondelete="CASCADE"), nullable=False)
    perceived_event_id: Mapped[str | None] = mapped_column(ForeignKey("events.id", ondelete="SET NULL"))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)


class BeliefState(TimestampMixin, Base):
    """A belief proposition held by a character with probability + evidence (spec §9.2)."""

    __tablename__ = "belief_states"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    character_id: Mapped[str] = mapped_column(ForeignKey("characters.id", ondelete="CASCADE"), nullable=False)
    scene_id: Mapped[str] = mapped_column(ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False)
    proposition: Mapped[str] = mapped_column(Text, nullable=False)
    probability: Mapped[float] = mapped_column(Float, default=0.5)
    source: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    evidence: Mapped[list] = mapped_column(JSON, default=list)


class Goal(TimestampMixin, Base):
    """Character goal with lifecycle (spec §9.2, §72)."""

    __tablename__ = "goals"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    character_id: Mapped[str] = mapped_column(ForeignKey("characters.id", ondelete="CASCADE"), nullable=False)
    scene_id: Mapped[str | None] = mapped_column(ForeignKey("scenes.id", ondelete="SET NULL"))
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    lifecycle: Mapped[str] = mapped_column(String(32), default="active")  # active|blocked|completed
    strength: Mapped[float] = mapped_column(Float, default=0.5)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
