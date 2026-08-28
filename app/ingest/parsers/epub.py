"""EPUB parser (spec §6.1).

An EPUB is a ZIP of (X)HTML content documents plus package metadata. We read it
with the standard library only (``zipfile`` + ``xml.etree`` + ``html.parser``):

    META-INF/container.xml
        -> OPF package path
            -> manifest (id -> href) + spine (reading order)
                -> each content document, text extracted in spine order

``<h1>``/``<h2>`` become structured headings (level 1 / 2); all other text is
flattened to prose lines.
"""
from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
import zipfile
from html.parser import HTMLParser

from app.ingest.normalize import decode_bytes
from app.ingest.parsers.base import BaseParser, ParserError
from app.ingest.types import Heading, ParsedDocument

_OPF_NS = {
    "opf": "http://www.idpf.org/2007/opf",
    "dc": "http://purl.org/dc/elements/1.1/",
}
_CONTAINER_NS = {"c": "urn:oasis:names:tc:opendocument:xmlns:container"}
_BLOCK_TAGS = {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "br", "tr", "section"}
_HEADING_TAGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.headings: list[Heading] = []
        self._offset = 0
        self._buf = ""

    def _flush(self) -> None:
        if self._buf:
            self.parts.append(self._buf)
            self._offset += len(self._buf) + 1
            self._buf = ""

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in _HEADING_TAGS:
            self._flush()
        elif tag in ("br",):
            self._buf += "\n"
        elif tag in _BLOCK_TAGS:
            self._flush()

    def handle_endtag(self, tag: str) -> None:
        if tag in _HEADING_TAGS:
            text = self._buf.strip()
            if text:
                self.headings.append(Heading(level=_HEADING_TAGS[tag], title=text, char_offset=self._offset))
            self._flush()
        elif tag in _BLOCK_TAGS:
            self._flush()

    def handle_data(self, data: str) -> None:
        # Collapse internal whitespace but keep newlines.
        cleaned = re.sub(r"[ \t]+", " ", data)
        self._buf += cleaned


def _find_opf_path(zf: zipfile.ZipFile) -> str:
    try:
        data = zf.read("META-INF/container.xml")
    except KeyError as exc:
        raise ParserError("EPUB missing META-INF/container.xml") from exc
    root = ET.fromstring(data)
    for rootfile in root.iter("{urn:oasis:names:tc:opendocument:xmlns:container}rootfile"):
        full = rootfile.get("full-path")
        if full:
            return full
    raise ParserError("EPUB container.xml has no rootfile")


def _read_opf(zf: zipfile.ZipFile, opf_path: str):
    data = zf.read(opf_path)
    root = ET.fromstring(data)
    manifest: dict[str, str] = {}
    manifest_el = root.find("opf:manifest", _OPF_NS) or root.find("manifest")
    if manifest_el is not None:
        for item in manifest_el:
            item_id = item.get("id")
            href = item.get("href")
            if item_id and href:
                manifest[item_id] = href
    spine_ids: list[str] = []
    spine_el = root.find("opf:spine", _OPF_NS) or root.find("spine")
    if spine_el is not None:
        for itemref in spine_el:
            ref = itemref.get("idref")
            if ref:
                spine_ids.append(ref)
    # Fall back to manifest order if the spine is empty.
    if not spine_ids:
        spine_ids = list(manifest.keys())
    return manifest, spine_ids, opf_path


def _resolve(href: str, base_opf: str) -> str:
    import posixpath

    return posixpath.normpath(posixpath.join(posixpath.dirname(base_opf), href))


class EpubParser(BaseParser):
    format = "epub"

    def parse(self, raw: bytes, filename: str | None = None) -> ParsedDocument:
        try:
            zf = zipfile.ZipFile(io.BytesIO(raw))
        except zipfile.BadZipFile as exc:
            raise ParserError("Not a valid EPUB/ZIP archive") from exc

        with zf:
            opf_path = _find_opf_path(zf)
            manifest, spine_ids, base = _read_opf(zf, opf_path)

            title: str | None = None
            author: str | None = None
            try:
                opf_root = ET.fromstring(zf.read(opf_path))
                meta = opf_root.find("opf:metadata", _OPF_NS) or opf_root.find("metadata")
                if meta is not None:
                    for el in meta:
                        tag = el.tag.split("}")[-1]
                        if tag == "title" and not title:
                            title = el.text
                        elif tag == "creator" and not author:
                            author = el.text
            except ET.ParseError:
                pass

            all_parts: list[str] = []
            all_headings: list[Heading] = []
            offset = 0
            for sid in spine_ids:
                href = manifest.get(sid)
                if not href:
                    continue
                path = _resolve(href, base)
                try:
                    content = zf.read(path)
                except KeyError:
                    continue
                html = decode_bytes(content)
                ex = _TextExtractor()
                ex.feed(html)
                # Re-base heading offsets to the running document offset.
                for h in ex.headings:
                    all_headings.append(Heading(level=h.level, title=h.title, char_offset=offset + h.char_offset))
                chunk = "\n".join(ex.parts).strip()
                if chunk:
                    all_parts.append(chunk)
                    offset += len(chunk) + 2

            text = "\n\n".join(all_parts).strip() + "\n"
            return ParsedDocument(text=text, title=title, author=author, format=self.format, headings=all_headings)
