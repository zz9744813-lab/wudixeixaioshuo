"""Text normalization for the ingestion pipeline (spec §6.2).

Encoding detection + light text normalization. We deliberately keep this
conservative: the raw bytes are preserved immutably in the object store, so the
normalized text here is only a *derivative* used for chapter/scene detection and
for the editable ``Chapter.raw_text`` column (spec §6.3).
"""
from __future__ import annotations

import re

# Encodings tried, in order, when decoding raw bytes. Chinese corpora commonly
# arrive as GBK, so it sits before the lossy latin-1 fallback.
_ENCODING_CANDIDATES = ("utf-8", "utf-8-sig", "gb18030", "gbk", "big5", "latin-1")

# Collapse runs of 3+ blank lines into a pair (keeps paragraph rhythm without
# giant gaps that would confuse the scene splitter).
_BLANK_RUN = re.compile(r"\n{3,}")


def decode_bytes(raw: bytes) -> str:
    """Decode raw file bytes, trying several encodings; never raises UnicodeError."""
    if not raw:
        return ""
    # utf-8-sig handles BOM; try strict utf-8 first.
    for enc in _ENCODING_CANDIDATES:
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    # Last resort: latin-1 never fails but may be mojibake; acceptable for a
    # best-effort ingest that the operator can re-run with a clean file.
    return raw.decode("latin-1", errors="replace")


def normalize_text(text: str) -> str:
    """Normalize line endings, strip BOM, collapse excessive blank lines."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if text.startswith("\ufeff"):
        text = text[1:]
    text = _BLANK_RUN.sub("\n\n", text)
    return text.strip() + "\n"
