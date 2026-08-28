"""Line-index helper shared by the chapter and scene detectors.

Both detectors reason about *lines* (paragraph boundaries), so we build a single
index of ``(char_start, text, heading_level)`` once and reuse it. Heading levels
come from the structured parse (Markdown ``#``/``##``, EPUB ``<h1>``/``<h2>``, DOCX
heading styles); plain-text files have no structured headings and rely on regex.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from app.ingest.types import Heading


@dataclass
class Line:
    char_start: int
    text: str
    heading_level: Optional[int]  # None when the line is not a structured heading


def build_line_index(text: str, headings: List[Heading]) -> List[Line]:
    lines: List[Line] = []
    offset = 0
    # Map a heading's char_offset to its line index for O(1) lookup.
    heading_by_offset = {h.char_offset: h.level for h in headings}
    for raw in text.split("\n"):
        level = heading_by_offset.get(offset)
        lines.append(Line(char_start=offset, text=raw, heading_level=level))
        offset += len(raw) + 1
    return lines
