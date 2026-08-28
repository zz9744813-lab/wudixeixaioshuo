"""LLM provider protocol + shared helpers (spec §29, §35)."""
from __future__ import annotations

import json
import re
from typing import List, Optional, Protocol, runtime_checkable

from pydantic import BaseModel


@runtime_checkable
class LLMProvider(Protocol):
    """Any LLM backend the Agents call. ``complete`` returns raw text; the Agent
    parses it into a structured model."""

    name: str

    def complete(
        self,
        messages: List["LLMMessage"],
        *,
        output_model: Optional[type[BaseModel]] = None,
        temperature: float = 0.2,
        **kwargs,
    ) -> str:
        ...


class LLMMessage(BaseModel):
    role: str  # system | user | assistant
    content: str


_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)
_OBJ_RE = re.compile(r"\{.*\}|\[.*\]", re.DOTALL)


def extract_json(text: str):
    """Best-effort extraction of a JSON object/array from an LLM response.

    Tries: raw parse -> strip code fences -> first balanced {..} / [..]. Returns
    ``None`` if nothing parseable (caller decides how to handle).
    """
    if text is None:
        return None
    candidates = [text.strip()]
    fenced = _JSON_FENCE.search(text)
    if fenced:
        candidates.append(fenced.group(1))
    obj = _OBJ_RE.search(text)
    if obj:
        candidates.append(obj.group(0))
    for c in candidates:
        try:
            return json.loads(c)
        except (json.JSONDecodeError, ValueError):
            continue
    return None
