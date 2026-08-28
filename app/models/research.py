"""Research Layer (spec §18–§20): Hypothesis → Experiment → Variant → Artifact.

Hypotheses must be falsifiable (§18.1). Experiments must declare
Changed/Fixed/Measured control variables (§19.1). Variants are control vs
treatment (§19.2).
"""
from __future__ import annotations

from sqlalchemy import (
    ForeignKey,
    JSON,
    String,
    Text,
    Float,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models._mixin import TimestampMixin
from app.models.enums import (
    HypothesisStatus,
    ExperimentStatus,
    VariantType,
    ArtifactType,
)


class Hypothesis(TimestampMixin, Base):
    __tablename__ = "hypotheses"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    independent_variables: Mapped[list] = mapped_column(JSON, default=list)
    dependent_variables: Mapped[list] = mapped_column(JSON, default=list)
    controls: Mapped[list] = mapped_column(JSON, default=list)
    scope: Mapped[str | None] = mapped_column(Text)
    expected_direction: Mapped[str | None] = mapped_column(Text)
    falsification_condition: Mapped[str | None] = mapped_column(Text)
    origin_evidence: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[HypothesisStatus] = mapped_column(default=HypothesisStatus.PROPOSED, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)


class Experiment(TimestampMixin, Base):
    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    hypothesis_id: Mapped[str] = mapped_column(
        ForeignKey("hypotheses.id", ondelete="CASCADE"), nullable=False
    )
    fixed: Mapped[dict] = mapped_column(JSON, default=dict)
    measurements: Mapped[list] = mapped_column(JSON, default=list)
    evaluation: Mapped[dict] = mapped_column(JSON, default=dict)  # {blind_pairwise, multi_judge, ...}
    falsification: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ExperimentStatus] = mapped_column(default=ExperimentStatus.DESIGNED, nullable=False)

    variants: Mapped[list["ExperimentVariant"]] = relationship(
        back_populates="experiment", cascade="all, delete-orphan"
    )


class ExperimentVariant(TimestampMixin, Base):
    __tablename__ = "experiment_variants"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    experiment_id: Mapped[str] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False
    )
    label: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g. control / treatment_A
    variant_type: Mapped[VariantType] = mapped_column(nullable=False)
    changed: Mapped[dict] = mapped_column(JSON, default=dict)
    fixed: Mapped[dict] = mapped_column(JSON, default=dict)
    measured: Mapped[dict] = mapped_column(JSON, default=dict)
    prompt_version: Mapped[str | None] = mapped_column(String(64))

    experiment: Mapped["Experiment"] = relationship(back_populates="variants")


class Artifact(TimestampMixin, Base):
    """Any derivative output: scene genome, rollout tree, report, raw output (spec §38)."""

    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    type: Mapped[ArtifactType] = mapped_column(nullable=False)
    parent_type: Mapped[str | None] = mapped_column(String(64))   # e.g. experiment / hypothesis / scene
    parent_id: Mapped[str | None] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    storage_ref: Mapped[str | None] = mapped_column(String(1024))  # object store path for big artifacts
    source_class: Mapped[str] = mapped_column(String(32), default="human_original")
    schema_version: Mapped[str] = mapped_column(String(16), default="1.0")
