"""Corpus ingestion pipeline (spec §6, EPIC-B).

Turns an uploaded novel file (TXT / MD / EPUB / DOCX) into a registered
``CorpusSource`` + ``Book`` + ``Chapter`` / ``Scene`` / ``SceneSpan`` rows.

The pipeline is deliberately **LLM-free** (matching the staged plan): parsing,
chapter detection, scene splitting and duplicate detection are all rule-based so
the existing schema can be fed real books end-to-end before the EPIC-C analysis
agents are built. Every downstream step only ever creates derivative artifacts;
the immutable raw bytes are preserved in the object store (spec §6.3).
"""
from __future__ import annotations

from app.ingest.service import ingest_bytes
from app.ingest.types import (
    ChapterBlock,
    Heading,
    IngestResult,
    ParsedDocument,
    SceneBlock,
)

__all__ = [
    "ingest_bytes",
    "IngestResult",
    "ParsedDocument",
    "Heading",
    "ChapterBlock",
    "SceneBlock",
]
