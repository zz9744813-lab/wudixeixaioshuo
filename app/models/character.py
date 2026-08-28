"""Character World Model (spec §9): static identity + continuous dynamic state.

Per spec P-04, a CharacterState is derived from the previous state plus new
evidence — never re-guessed from scratch each scene (forbidden, spec §56 禁止8).
"""
from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models._mixin import TimestampMixin


class Character(TimestampMixin, Base):
    __tablename__ = "characters"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    book_id: Mapped[str] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    identity: Mapped[dict] = mapped_column(JSON, default=dict)
    background: Mapped[str | None] = mapped_column(Text)
    traits: Mapped[list] = mapped_column(JSON, default=list)
    values: Mapped[list] = mapped_column(JSON, default=list)
    habits: Mapped[list] = mapped_column(JSON, default=list)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    taboos: Mapped[list] = mapped_column(JSON, default=list)
    long_term_desires: Mapped[list] = mapped_column(JSON, default=list)
    core_fears: Mapped[list] = mapped_column(JSON, default=list)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)


class CharacterState(TimestampMixin, Base):
    """Continuous world-model state for one character at one scene (spec §9.2).

    Aggregates the per-dimension sub-states as JSON so the full State(t) is
    reconstructable and continuously updatable, while sibling tables
    (belief_states, knowledge_states, relationship_states, emotion_states,
    goals) keep individual facts queryable.
    """

    __tablename__ = "character_states"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    character_id: Mapped[str] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    scene_id: Mapped[str] = mapped_column(ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False)
    book_id: Mapped[str] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), nullable=False)

    goals: Mapped[dict] = mapped_column(JSON, default=dict)        # {active, blocked, completed}
    beliefs: Mapped[list] = mapped_column(JSON, default=list)       # list of {proposition_id, probability, source, confidence}
    knowledge: Mapped[list] = mapped_column(JSON, default=list)     # list of {fact_id, status, certainty}
    desires: Mapped[list] = mapped_column(JSON, default=list)       # list of {desire, strength}
    fears: Mapped[list] = mapped_column(JSON, default=list)         # list of {fear, strength}
    emotions: Mapped[list] = mapped_column(JSON, default=list)      # list of {emotion, intensity, cause}
    commitments: Mapped[list] = mapped_column(JSON, default=list)   # list of {commitment_id, strength, status}
    resources: Mapped[dict] = mapped_column(JSON, default=dict)     # {material, social, informational}
    constraints: Mapped[dict] = mapped_column(JSON, default=dict)   # {physical, moral, social, strategic}

    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    derived_from_state_id: Mapped[str | None] = mapped_column(String(64))  # previous State(t-1)

    character: Mapped["Character"] = relationship()
