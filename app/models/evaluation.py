"""Evaluation Layer (spec §21, §23): Reader profiles + Judgments.

Judge outputs are multi-dimensional, evidence-backed and pairwise-first; the
judge must NOT know model/prompt/group identity (§23.1–§23.3, 禁止7).
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
from app.models.enums import EvaluationType


class ReaderProfile(TimestampMixin, Base):
    """A simulated reader persona (spec §21.1). Weights drive Reader Simulator outputs."""

    __tablename__ = "reader_profiles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    patience: Mapped[float] = mapped_column(Float, default=0.5)
    pacing_preference: Mapped[float] = mapped_column(Float, default=0.5)
    novelty_preference: Mapped[float] = mapped_column(Float, default=0.5)
    logic_sensitivity: Mapped[float] = mapped_column(Float, default=0.5)
    prose_sensitivity: Mapped[float] = mapped_column(Float, default=0.5)
    character_attachment_weight: Mapped[float] = mapped_column(Float, default=0.5)
    romance_weight: Mapped[float] = mapped_column(Float, default=0.5)
    suspense_weight: Mapped[float] = mapped_column(Float, default=0.5)
    action_weight: Mapped[float] = mapped_column(Float, default=0.5)
    erotic_tension_weight: Mapped[float] = mapped_column(Float, default=0.5)
    tolerance_for_repetition: Mapped[float] = mapped_column(Float, default=0.5)
    tolerance_for_coincidence: Mapped[float] = mapped_column(Float, default=0.5)
    tolerance_for_exposition: Mapped[float] = mapped_column(Float, default=0.5)
    cliffhanger_preference: Mapped[float] = mapped_column(Float, default=0.5)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)


class Evaluation(TimestampMixin, Base):
    """A single judgment. Pairwise by default; anonymous by construction."""

    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    type: Mapped[EvaluationType] = mapped_column(nullable=False)
    subject_a_ref: Mapped[str | None] = mapped_column(String(256))
    subject_b_ref: Mapped[str | None] = mapped_column(String(256))
    winner: Mapped[str | None] = mapped_column(String(16))  # A | B | TIE
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    decisive_dimensions: Mapped[list] = mapped_column(JSON, default=list)
    evidence_spans: Mapped[list] = mapped_column(JSON, default=list)
    failure_reasons: Mapped[list] = mapped_column(JSON, default=list)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)  # per-dimension scores
    judge_model: Mapped[str | None] = mapped_column(String(128))  # logged, NOT shown to authors
    blind: Mapped[bool] = mapped_column(default=True)
