"""Claim / Evidence / Canonical system (spec §17).

Agent outputs first become Claims, never direct canonical writes (禁止3).
Claims carry evidence; a Reconciler later promotes them to canonical state.
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
from app.models.enums import EvidenceType


class Claim(TimestampMixin, Base):
    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    subject: Mapped[str] = mapped_column(String(256), nullable=False)
    predicate: Mapped[str] = mapped_column(String(256), nullable=False)
    object: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    agent_run: Mapped[str | None] = mapped_column(String(64))
    scope: Mapped[str | None] = mapped_column(String(64))  # e.g. scene/character/book
    status: Mapped[str] = mapped_column(String(32), default="open")  # open|reconciled|rejected
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)

    evidence: Mapped[list["Evidence"]] = relationship(
        back_populates="claim", cascade="all, delete-orphan"
    )


class Evidence(TimestampMixin, Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    claim_id: Mapped[str] = mapped_column(
        ForeignKey("claims.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[EvidenceType] = mapped_column(nullable=False)
    source_span_id: Mapped[str | None] = mapped_column(String(64))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    external_ref: Mapped[str | None] = mapped_column(String(512))

    claim: Mapped["Claim"] = relationship(back_populates="evidence")
