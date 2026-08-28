"""User feedback & Personal Taste Model (spec §25).

Raw feedback is never a rule. A Taste Interpreter proposes candidate causes
with confidence; an aesthetic vector captures preferences (§25.2).
"""
from __future__ import annotations

from sqlalchemy import (
    JSON,
    String,
    Text,
    Float,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models._mixin import TimestampMixin


class UserFeedback(TimestampMixin, Base):
    __tablename__ = "user_feedback"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(String(64))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    interpretation: Mapped[list] = mapped_column(JSON, default=list)  # candidate causes w/ confidence
    taste_vector: Mapped[dict] = mapped_column(JSON, default=dict)     # {pacing, novelty, ...}
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[str] = mapped_column(String(32), default="user_feedback")
