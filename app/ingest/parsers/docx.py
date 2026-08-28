"""DOCX parser (spec §6.1).

A ``.docx`` is a ZIP whose ``word/document.xml`` holds paragraphs (``<w:p>``) made
of runs (``<w:r>`` / ``<w:t>``). We extract paragraph text with the standard
library (``zipfile`` + ``xml.etree``), and treat Word heading styles
(``Heading1`` .. ``HeadingN`` / ``标题N``) as structured headings.
"""
from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
import zipfile

from app.ingest.normalize import decode_bytes
from app.ingest.parsers.base import BaseParser, ParserError
from app.ingest.types import Heading, ParsedDocument

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _heading_level_from_style(style_val: str | None) -> int | None:
    if not style_val:
        return None
    m = re.match(r"^(?:Heading|标题)\s*([0-9])", style_val, re.IGNORECASE)
    if m:
        return int(m.group(1))
    if style_val.lower() in ("title",):
        return 1
    return None


class _DocxExtractor:
    def __init__(self, root: ET.Element) -> None:
        self.root = root
        self.paragraphs: list[str] = []
        self.headings: list[Heading] = []
        self._offset = 0

    def run(self) -> None:
        body = self.root.find(f"{_W}body")
        if body is None:
            return
        for para in body.iter(f"{_W}p"):
            text = self._paragraph_text(para)
            style_val = self._paragraph_style(para)
            level = _heading_level_from_style(style_val)
            if level is not None and text.strip():
                self.headings.append(Heading(level=level, title=text.strip(), char_offset=self._offset))
            self.paragraphs.append(text)
            self._offset += len(text) + 1

    @staticmethod
    def _paragraph_text(para: ET.Element) -> str:
        parts: list[str] = []
        for t in para.iter(f"{_W}t"):
            if t.text:
                parts.append(t.text)
        # Preserve line breaks / tabs inside the paragraph.
        text = "".join(parts)
        text = text.replace("\t", "    ")
        return text.rstrip()

    @staticmethod
    def _paragraph_style(para: ET.Element) -> str | None:
        ppr = para.find(f"{_W}pPr")
        if ppr is None:
            return None
        ps = ppr.find(f"{_W}pStyle")
        if ps is None:
            return None
        return ps.get(f"{_W}val")


class DocxParser(BaseParser):
    format = "docx"

    def parse(self, raw: bytes, filename: str | None = None) -> ParsedDocument:
        try:
            zf = zipfile.ZipFile(io.BytesIO(raw))
        except zipfile.BadZipFile as exc:
            raise ParserError("Not a valid DOCX/ZIP archive") from exc

        with zf:
            try:
                data = zf.read("word/document.xml")
            except KeyError as exc:
                raise ParserError("DOCX missing word/document.xml") from exc
            root = ET.fromstring(data)

            title: str | None = None
            author: str | None = None
            try:
                core = zf.read("docProps/core.xml")

                def _dc(tag: str) -> str | None:
                    m = re.search(rf"<dc:{tag}[^>]*>(.*?)</dc:{tag}>", core.decode("utf-8", "replace"), re.S)
                    return m.group(1) if m else None

                title = _dc("title") or None
                author = _dc("creator") or None
            except KeyError:
                pass

            ex = _DocxExtractor(root)
            ex.run()
            text = "\n".join(ex.paragraphs).strip() + "\n"
            return ParsedDocument(
                text=text, title=title, author=author, format=self.format, headings=ex.headings
            )
