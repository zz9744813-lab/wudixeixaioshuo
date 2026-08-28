"""Plain-text parser (spec §6.1)."""
from __future__ import annotations

from app.ingest.normalize import decode_bytes, normalize_text
from app.ingest.parsers.base import BaseParser
from app.ingest.types import ParsedDocument


class TxtParser(BaseParser):
    format = "txt"

    def parse(self, raw: bytes, filename: str | None = None) -> ParsedDocument:
        text = normalize_text(decode_bytes(raw))
        # For plain text we cannot recover a title/author reliably; the caller
        # (corpus/ingest) supplies them via the form. Headings are detected
        # later by the chapter detector via regex, not by this parser.
        return ParsedDocument(text=text, title=None, author=None, format=self.format)
