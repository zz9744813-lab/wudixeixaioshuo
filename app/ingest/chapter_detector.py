"""Chapter detection (spec §6.2, §7).

A line starts a new Chapter when it matches a chapter-heading pattern
(``第N章`` / ``Chapter N`` / ``卷`` / ``部`` / ``Part N``) **or** is a structured
top-level heading (Markdown ``#`` / EPUB ``<h1>`` / DOCX ``Heading1``). If no
boundary is found the whole document is a single Chapter (spec §7 permits coarse
fallbacks). A preamble before the first chapter becomes Chapter 0.

This is a rule-based, LLM-free step: it never "guesses" content, only splits on
explicit structural signals, so it stays falsifiable and reproducible (spec P-06).
"""
from __future__ import annotations

import re
from typing import List, Optional

from app.ingest.lines import build_line_index
from app.ingest.types import ChapterBlock, Heading

_CHAPTER_RE = [
    re.compile(r"^第\s*[零一二三四五六七八九十百千〇0-9]+\s*章\b"),
    re.compile(r"^第\s*[零一二三四五六七八九十百千〇0-9]+\s*节\b"),
    re.compile(r"^第\s*[零一二三四五六七八九十百千〇0-9]+\s*卷\b"),
    re.compile(r"^卷\s*[一二三四五六七八九十百千0-9]+"),
    re.compile(r"^部\s*[一二三四五六七八九十百千0-9]+"),
    re.compile(r"^Chapter\s+\d+", re.IGNORECASE),
    re.compile(r"^Part\s+\d+", re.IGNORECASE),
]

_TITLE_CLEAN = re.compile(
    r"^(第\s*[零一二三四五六七八九十百千〇0-9]+\s*[章章节卷部]|"
    r"Chapter\s+\d+|Part\s+\d+|#+\s*)\s*",
    re.IGNORECASE,
)


def _is_chapter_line(line: str, level: Optional[int]) -> bool:
    if level is not None and level <= 1:
        return True
    s = line.strip()
    return any(p.match(s) for p in _CHAPTER_RE)


def _clean_title(s: str) -> Optional[str]:
    title = _TITLE_CLEAN.sub("", s.strip()).strip()
    return title or None


def detect_chapters(text: str, headings: List[Heading]) -> List[ChapterBlock]:
    lines = build_line_index(text, headings)

    boundaries: List[tuple[int, int, Optional[str]]] = []  # (line_idx, char_start, title)
    for idx, line in enumerate(lines):
        if _is_chapter_line(line.text, line.heading_level):
            boundaries.append((idx, line.char_start, _clean_title(line.text)))
    # De-duplicate consecutive boundaries on the same offset (e.g. heading +
    # a duplicated marker line).
    seen = set()
    unique: List[tuple[int, int, Optional[str]]] = []
    for b in boundaries:
        if b[1] in seen:
            continue
        seen.add(b[1])
        unique.append(b)

    if not unique:
        return [
            ChapterBlock(
                index=0, title=None, raw_text=text.strip(), char_start=0, char_end=len(text)
            )
        ]

    blocks: List[ChapterBlock] = []
    # Preamble: text before the first chapter boundary.
    if unique[0][1] > 0:
        blocks.append(
            ChapterBlock(
                index=0,
                title=None,
                raw_text=text[: unique[0][1]].strip(),
                char_start=0,
                char_end=unique[0][1],
            )
        )

    for k, (line_idx, start, title) in enumerate(unique):
        end = unique[k + 1][1] if k + 1 < len(unique) else len(text)
        blocks.append(
            ChapterBlock(
                index=len(blocks),
                title=title,
                raw_text=text[start:end].strip(),
                char_start=start,
                char_end=end,
            )
        )

    # Drop an empty preamble block if it produced no content.
    blocks = [b for b in blocks if b.raw_text.strip()]
    for new_idx, b in enumerate(blocks):
        b.index = new_idx
    return blocks
