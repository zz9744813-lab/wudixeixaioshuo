"""Relationship Model (spec §11): a relationship is a vector of dimensions,
not a single 'like' score. Each dimension tracks value/confidence/cause/last_changed_scene.
"""
from __future__ import annotations

from sqlalchemy import (
    ForeignKey,
    JSON,
    Float,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models._mixin import TimestampMixin
from app.models.enums import RelationshipDimension


class RelationshipState(TimestampMixin, Base):
    __tablename__ = "relationship_states"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    book_id: Mapped[str] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    scene_id: Mapped[str] = mapped_column(ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False)
    from_character_id: Mapped[str] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    to_character_id: Mapped[str] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    # vector of {dimension, value, confidence, cause, last_changed_scene}
    dimensions: Mapped[list] = mapped_column(JSON, default=list)
    overall: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    def get_dimension(self, dim: RelationshipDimension) -> float | None:
        for d in self.dimensions or []:
            if d.get("dimension") == dim.value:
                return d.get("value")
        return None
