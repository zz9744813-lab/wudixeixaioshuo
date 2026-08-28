"""Format parsers (spec §6.1): TXT / MD / EPUB / DOCX.

Each parser converts a file's raw bytes into a :class:`ParsedDocument` (normalized
plain text + discovered headings). All parsers use the Python standard library
only, so no extra dependencies are required at this stage.

Select a parser with :func:`get_parser` (by file extension), then call
``parser.parse(raw, filename)``.
"""
from __future__ import annotations

from app.ingest.parsers.base import BaseParser, ParserError
from app.ingest.parsers.docx import DocxParser
from app.ingest.parsers.epub import EpubParser
from app.ingest.parsers.md import MarkdownParser
from app.ingest.parsers.txt import TxtParser
from app.ingest.types import ParsedDocument

_PARSERS = {
    "txt": TxtParser,
    "text": TxtParser,
    "md": MarkdownParser,
    "markdown": MarkdownParser,
    "epub": EpubParser,
    "docx": DocxParser,
    "doc": DocxParser,
}


def extension_of(filename: str | None) -> str:
    if not filename:
        return "txt"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
    return ext or "txt"


def get_parser(filename: str | None) -> BaseParser:
    """Return a parser instance appropriate for ``filename`` (falls back to TXT)."""
    ext = extension_of(filename)
    cls = _PARSERS.get(ext, TxtParser)
    return cls()


def parse_bytes(raw: bytes, filename: str | None = None) -> ParsedDocument:
    """One-shot: pick a parser by extension and parse the raw bytes."""
    return get_parser(filename).parse(raw, filename)


__all__ = [
    "BaseParser",
    "ParserError",
    "TxtParser",
    "MarkdownParser",
    "EpubParser",
    "DocxParser",
    "get_parser",
    "parse_bytes",
    "extension_of",
]
