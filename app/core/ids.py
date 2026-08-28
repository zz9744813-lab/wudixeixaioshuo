"""ID system (spec §36 EPIC-A).

Semantic, prefixed, globally-unique identifiers such as ``BOOK-01``,
``SCENE-00128``, ``RUN-...``. We keep them unique without a central sequence
by combining a zero-padded counter seed with a short random suffix; the prefix
carries the object class so every ID is self-describing and traceable.
"""
from __future__ import annotations

import uuid

_PREFIX_WIDTH = 4


def new_id(prefix: str) -> str:
    """Return a prefixed id, e.g. ``new_id("SCENE")`` -> ``SCENE-7F3A91K2``."""
    suffix = uuid.uuid4().hex[:8].upper()
    return f"{prefix.upper()}-{suffix}"


def run_id() -> str:
    return new_id("RUN")


def context_package_id() -> str:
    return new_id("CP")


def scene_span_id() -> str:
    return new_id("SPAN")
