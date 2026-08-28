"""Parser protocol + shared errors."""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.ingest.types import ParsedDocument


class ParserError(Exception):
    """Raised when a file cannot be parsed by its designated parser."""


class BaseParser(ABC):
    """Subclasses turn raw bytes into a normalized :class:`ParsedDocument`."""

    format: str = "txt"

    @abstractmethod
    def parse(self, raw: bytes, filename: str | None = None) -> ParsedDocument:
        """Decode + normalize ``raw`` into a :class:`ParsedDocument`."""
        raise NotImplementedError
