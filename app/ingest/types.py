"""Shared data types for the ingestion pipeline (spec §6, §7, §36)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from typing import List


@dataclass
class Heading:
    """A structural heading discovered by a parser, with its byte offset."""

    level: int  # 1 = top-level chapter, 2 = section, ...
    title: str
    char_offset: int  # offset of the heading line within the full parsed text


@dataclass
class ParsedDocument:
    """Normalized plain-text view of an ingested source."""

    text: str
    title: Optional[str]
    author: Optional[str]
    format: str  # txt | md | epub | docx
    headings: List[Heading] = field(default_factory=list)


@dataclass
class Paragraph:
    char_start: int
    char_end: int
    text: str


@dataclass
class SceneBlock:
    """One Scene inside a Chapter (spec §7). Offsets are within the chapter text."""

    index: int
    raw_text: str
    char_start: int
    char_end: int
    paragraphs: List[Paragraph] = field(default_factory=list)
    heuristic: bool = False  # True when produced by the size-based fallback splitter


@dataclass
class ChapterBlock:
    """One Chapter inside a Book (spec §7). Offsets are within the full text."""

    index: int
    title: Optional[str]
    raw_text: str
    char_start: int
    char_end: int
    scenes: List[SceneBlock] = field(default_factory=list)


@dataclass
class IngestResult:
    """Machine-readable outcome of an ingest run (returned by the API)."""

    book_id: str
    source_id: Optional[str]
    task_id: str
    chapter_count: int
    scene_count: int
    span_count: int
    duplicate_groups: List[List[str]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    idempotent: bool = False

    def to_dict(self) -> dict:
        return {
            "book_id": self.book_id,
            "source_id": self.source_id,
            "task_id": self.task_id,
            "chapter_count": self.chapter_count,
            "scene_count": self.scene_count,
            "span_count": self.span_count,
            "duplicate_groups": self.duplicate_groups,
            "warnings": self.warnings,
            "idempotent": self.idempotent,
        }
