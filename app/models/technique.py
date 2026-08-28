"""Technique Ontology (spec §15) and Behavior Patterns (spec §62).

A Technique is a fully-specified object: mechanism, preconditions, failure
modes, counterexamples, evidence and scope. It must carry counterexamples
(spec §7 禁止5) and only reaches production after the promotion gate (§26, §51).
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
from app.models.enums import (
    TechniqueCategory,
    KnowledgeTier,
)


class Technique(TimestampMixin, Base):
    __tablename__ = "techniques"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    category: Mapped[TechniqueCategory] = mapped_column(nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    mechanism: Mapped[list] = mapped_column(JSON, default=list)
    preconditions: Mapped[list] = mapped_column(JSON, default=list)
    execution: Mapped[list] = mapped_column(JSON, default=list)
    expected_effects: Mapped[dict] = mapped_column(JSON, default=dict)
    failure_modes: Mapped[list] = mapped_column(JSON, default=list)
    scope: Mapped[dict] = mapped_column(JSON, default=dict)  # {genre: level}
    counterexamples: Mapped[list] = mapped_column(JSON, default=list)
    evidence_count: Mapped[int] = mapped_column(default=0)
    experiment_ids: Mapped[list] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[KnowledgeTier] = mapped_column(default=KnowledgeTier.OBSERVATION, nullable=False)
    source_class: Mapped[str] = mapped_column(String(32), default="human_original")


class BehaviorPattern(TimestampMixin, Base):
    """Reusable behavior rule triggered by a perceptual/appraisal condition (spec §62)."""

    __tablename__ = "behavior_patterns"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    trigger: Mapped[str] = mapped_column(String(256), nullable=False)
    prerequisites: Mapped[dict] = mapped_column(JSON, default=dict)
    modifiers: Mapped[list] = mapped_column(JSON, default=list)
    candidate_actions: Mapped[dict] = mapped_column(JSON, default=dict)  # {action: weight}
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    exceptions: Mapped[list] = mapped_column(JSON, default=list)
    scope: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[KnowledgeTier] = mapped_column(default=KnowledgeTier.OBSERVATION, nullable=False)
