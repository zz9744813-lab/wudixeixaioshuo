"""Benchmark suite (spec §24, §47). Golden cases are immutable and versioned."""
from __future__ import annotations

from sqlalchemy import (
    JSON,
    String,
    Text,
    Boolean,
    Float,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models._mixin import TimestampMixin
from app.models.enums import BenchName, SourceClass


class BenchmarkCase(TimestampMixin, Base):
    __tablename__ = "benchmark_cases"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    bench: Mapped[BenchName] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    input_ref: Mapped[dict] = mapped_column(JSON, default=dict)
    expected: Mapped[dict] = mapped_column(JSON, default=dict)   # gold answer
    gold: Mapped[bool] = mapped_column(Boolean, default=True)    # part of Golden Set (§47)
    frozen: Mapped[bool] = mapped_column(Boolean, default=True)  # never auto-overwritten
    source_class: Mapped[SourceClass] = mapped_column(default=SourceClass.HUMAN_ORIGINAL, nullable=False)
    version: Mapped[str] = mapped_column(String(16), default="1.0")


class BenchmarkRun(TimestampMixin, Base):
    __tablename__ = "benchmark_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    bench: Mapped[BenchName] = mapped_column(nullable=False)
    case_id: Mapped[str] = mapped_column(ForeignKey("benchmark_cases.id", ondelete="CASCADE"), nullable=False)
    subject_ref: Mapped[str | None] = mapped_column(String(256))   # model/technique/prompt under test
    prediction: Mapped[dict] = mapped_column(JSON, default=dict)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    judge_model: Mapped[str | None] = mapped_column(String(128))
    passed: Mapped[bool | None] = mapped_column()
