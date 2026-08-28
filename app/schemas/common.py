"""Common API schemas: pagination, standard envelopes."""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class Message(BaseModel):
    detail: str
    code: str | None = None


class HealthStatus(BaseModel):
    app: str
    status: str = "ok"
    schema_version: str
    tables: int
