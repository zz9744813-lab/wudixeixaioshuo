"""Research Knowledge Graph edges (spec §27)."""
from __future__ import annotations

from sqlalchemy import (
    ForeignKey,
    JSON,
    String,
    Float,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models._mixin import TimestampMixin
from app.models.enums import ResearchEdgeType


class ResearchEdge(TimestampMixin, Base):
    __tablename__ = "research_edges"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    from_type: Mapped[str] = mapped_column(String(64), nullable=False)   # node type
    from_id: Mapped[str] = mapped_column(String(64), nullable=False)
    to_type: Mapped[str] = mapped_column(String(64), nullable=False)
    to_id: Mapped[str] = mapped_column(String(64), nullable=False)
    type: Mapped[ResearchEdgeType] = mapped_column(nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
