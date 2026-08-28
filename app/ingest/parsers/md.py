"""Markdown parser (spec §6.1).

Converts Markdown to plain text while preserving heading structure. Headings
(``#`` / ``##`` / ...) become normal lines (so the chapter detector can see them)
and are also recorded with their level + offset for structured detection. Inline
syntax (emphasis, links, images, inline code) is stripped so downstream detection
operates on clean prose.
"""
from __future__ import annotations

import re

from app.ingest.normalize import decode_bytes, normalize_text
from app.ingest.parsers.base import BaseParser, ParserError
from app.ingest.types import Heading, ParsedDocument

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_SETEX_UNDERLINE = re.compile(r"^[-=]{3,}\s*$")
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_EMPHASIS = re.compile(r"(\*\*|__|\*|_|`)")


class MarkdownParser(BaseParser):
    format = "md"

    def parse(self, raw: bytes, filename: str | None = None) -> ParsedDocument:
        text = normalize_text(decode_bytes(raw))
        lines = text.split("\n")

        out_lines: list[str] = []
        headings: list[Heading] = []
        offset = 0
        prev_line_blank = True

        for line in lines:
            m = _HEADING.match(line)
            if m:
                level = len(m.group(1))
                title = _clean_inline(m.group(2)).strip()
                out_lines.append(title)  # keep the heading text as a plain line
                headings.append(Heading(level=level, title=title, char_offset=offset))
                offset += len(title) + 1
                prev_line_blank = True
                continue

            # Setext headings: a line of === or --- under a non-empty line.
            if _SETEX_UNDERLINE.match(line) and prev_line_blank is False and lines and out_lines:
                # Promote the previous line to a heading (level 1 for =, 2 for -).
                level = 1 if line.startswith("=") else 2
                prev_text = out_lines[-1]
                headings.append(
                    Heading(level=level, title=prev_text, char_offset=offset - len(prev_text) - 1)
                )
                offset += len(line) + 1
                prev_line_blank = True
                continue

            cleaned = _clean_inline(line).strip()
            out_lines.append(cleaned)
            offset += len(line) + 1
            prev_line_blank = line.strip() == ""

        result = "\n".join(out_lines).strip() + "\n"
        return ParsedDocument(text=result, title=None, author=None, format=self.format, headings=headings)


def _clean_inline(s: str) -> str:
    s = _IMAGE.sub("", s)
    s = _LINK.sub(r"\1", s)  # keep link text, drop the URL
    s = _EMPHASIS.sub("", s)
    return s
