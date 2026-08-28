"""Agent I/O protocol (spec §31).

Every Agent MUST emit this structured envelope. Free text only enters the
``explanation`` field — it is never the primary machine interface (§31.1).
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgentOutput(BaseModel):
    schema_version: str = Field(default="1.0")
    run_id: str
    status: str = Field(default="ok")  # ok | partial | failed
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    data: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    explanation: str | None = None


class AgentInput(BaseModel):
    """Minimal contract an Agent receives alongside a ContextPackage."""

    task: str
    context_package_id: str | None = None
    prompt_version: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
