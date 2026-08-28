"""Emotion & Appraisal model (spec §12). Never a bare label: every emotion
carries trigger_event, appraisal vector, action_tendency and evidence.
"""
from __future__ import annotations

from sqlalchemy import (
    ForeignKey,
    JSON,
    Float,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models._mixin import TimestampMixin
from app.models.enums import EmotionType


class EmotionState(TimestampMixin, Base):
    __tablename__ = "emotion_states"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    character_id: Mapped[str] = mapped_column(ForeignKey("characters.id", ondelete="CASCADE"), nullable=False)
    scene_id: Mapped[str] = mapped_column(ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False)
    emotion: Mapped[EmotionType] = mapped_column(nullable=False)
    intensity: Mapped[float] = mapped_column(Float, default=0.0)
    trigger_event_id: Mapped[str | None] = mapped_column(ForeignKey("events.id", ondelete="SET NULL"))
    appraisal: Mapped[dict] = mapped_column(JSON, default=dict)       # {dimension: value}
    action_tendency: Mapped[dict] = mapped_column(JSON, default=dict)  # {tendency: weight}
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
