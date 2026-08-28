"""Corpus Layer (spec §6, §36): sources → books → chapters → scenes → spans.

Raw text is immutable (spec §6.3); every downstream step only ever creates
derivative artifacts, never overwrites the source.
"""
from __future__ import annotations

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models._mixin import TimestampMixin
from app.models.enums import SourceClass


class CorpusSource(TimestampMixin, Base):
    __tablename__ = "corpus_sources"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    author: Mapped[str | None] = mapped_column(String(256))
    source_class: Mapped[SourceClass] = mapped_column(
        default=SourceClass.HUMAN_ORIGINAL, nullable=False
    )
    format: Mapped[str] = mapped_column(String(32), default="txt", nullable=False)
    raw_path: Mapped[str | None] = mapped_column(String(1024))  # immutable raw copy
    language: Mapped[str | None] = mapped_column(String(16))
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    imported_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True))


class Book(TimestampMixin, Base):
    __tablename__ = "books"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    corpus_source_id: Mapped[str | None] = mapped_column(
        ForeignKey("corpus_sources.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    author: Mapped[str | None] = mapped_column(String(256))
    genre: Mapped[str | None] = mapped_column(String(128))
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)

    chapters: Mapped[list["Chapter"]] = relationship(
        back_populates="book", cascade="all, delete-orphan"
    )


class Chapter(TimestampMixin, Base):
    __tablename__ = "chapters"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    book_id: Mapped[str] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), nullable=False
    )
    index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    title: Mapped[str | None] = mapped_column(String(512))
    raw_text: Mapped[str | None] = mapped_column(Text)  # cleaned derivative, not the immutable source
    word_count: Mapped[int] = mapped_column(Integer, default=0)

    book: Mapped["Book"] = relationship(back_populates="chapters")
    scenes: Mapped[list["Scene"]] = relationship(
        back_populates="chapter", cascade="all, delete-orphan"
    )


class Scene(TimestampMixin, Base):
    """Smallest primary research unit (spec §7). Carries entry/exit state and
    the canonical 'Scene Genome' aggregated view as JSON."""

    __tablename__ = "scenes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    book_id: Mapped[str] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), nullable=False
    )
    chapter_id: Mapped[str] = mapped_column(
        ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False
    )
    index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pov: Mapped[str | None] = mapped_column(String(64))
    time: Mapped[str | None] = mapped_column(String(256))
    location: Mapped[str | None] = mapped_column(String(256))
    participants: Mapped[list] = mapped_column(JSON, default=list)
    scene_goal: Mapped[str | None] = mapped_column(Text)
    dominant_conflict: Mapped[str | None] = mapped_column(String(256))
    narrative_functions: Mapped[list] = mapped_column(JSON, default=list)
    entry_state: Mapped[dict] = mapped_column(JSON, default=dict)
    exit_state: Mapped[dict] = mapped_column(JSON, default=dict)
    summary: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(default=0.0)
    source_range: Mapped[dict] = mapped_column(JSON, default=dict)
    genome: Mapped[dict] = mapped_column(JSON, default=dict)  # canonical Scene Genome
    analyzed: Mapped[bool] = mapped_column(Boolean, default=False)

    chapter: Mapped["Chapter"] = relationship(back_populates="scenes")
    spans: Mapped[list["SceneSpan"]] = relationship(
        back_populates="scene", cascade="all, delete-orphan"
    )


class SceneSpan(TimestampMixin, Base):
    """Addressable text spans inside a Scene, the leaf unit for Evidence (spec §17)."""

    __tablename__ = "scene_spans"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scene_id: Mapped[str] = mapped_column(
        ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False
    )
    char_start: Mapped[int] = mapped_column(Integer, default=0)
    char_end: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    annotation: Mapped[dict] = mapped_column(JSON, default=dict)

    scene: Mapped["Scene"] = relationship(back_populates="spans")
