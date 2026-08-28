"""Knowledge Layer (spec §26, §27, §63): validated rules with promotion ladder.

Only VALIDATED+ rules may be recommended to NovelForge (P-10, §26.1). The
promotion gate (§51) requires mechanism, preconditions, failure modes, multiple
evidence sources, a counterexample, a counterfactual experiment, an independent
judge, cross-sample reproduction, and VALIDATED status.
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
from app.models.enums import KnowledgeTier, TechniqueCategory


class KnowledgeRule(TimestampMixin, Base):
    __tablename__ = "knowledge_rules"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[TechniqueCategory | None] = mapped_column()
    tier: Mapped[KnowledgeTier] = mapped_column(default=KnowledgeTier.OBSERVATION, nullable=False)
    mechanism: Mapped[str | None] = mapped_column(Text)
    preconditions: Mapped[list] = mapped_column(JSON, default=list)
    failure_modes: Mapped[list] = mapped_column(JSON, default=list)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    counterexamples: Mapped[list] = mapped_column(JSON, default=list)
    experiment_ids: Mapped[list] = mapped_column(JSON, default=list)
    reproduction_count: Mapped[int] = mapped_column(default=0)
    judge_agreement: Mapped[float] = mapped_column(Float, default=0.0)
    production_evidence: Mapped[list] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    scope: Mapped[dict] = mapped_column(JSON, default=dict)
    parent_technique_id: Mapped[str | None] = mapped_column(
        ForeignKey("techniques.id", ondelete="SET NULL")
    )
