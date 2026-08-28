"""Deterministic fake LLM provider (spec §39 offline mode).

Returns schema-valid, content-free output so the whole multi-pass pipeline is
runnable and testable without an API key. It introspects the requested
``output_model`` and fills every field with a safe default, so downstream
parsing/validation never crashes. This is explicitly a *demo* provider — it does
not "understand" the novel; real analysis requires a configured model.
"""
from __future__ import annotations

from typing import Any, List, Optional, Type

from pydantic import BaseModel
from pydantic_core import PydanticUndefined

from app.llm.provider import LLMMessage


def _fill(model: Type[BaseModel]) -> dict:
    out: dict[str, Any] = {}
    for name, field in model.model_fields.items():
        raw = field.default
        default = None if raw is PydanticUndefined else raw
        out[name] = _default_for_type(field.annotation, default)
    return out


def _default_for_type(annotation: Any, fallback) -> Any:
    from typing import get_origin, get_args, Union

    if fallback is not None and fallback is not PydanticUndefined:
        return fallback
    # Unwrap Optional[...] / Union
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is Union and type(None) in args:
        non_none = [a for a in args if a is not type(None)]
        if non_none:
            annotation = non_none[0]
            origin = get_origin(annotation)
            args = get_args(annotation)
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return _fill(annotation)
    if origin in (list, List):
        return []
    if origin is dict:
        return {}
    if annotation is str:
        return "[fake]"
    if annotation is bool:
        return False
    if annotation in (int, float):
        return 0.0
    return None


class FakeProvider:
    name = "fake"

    def __init__(self, db=None, note: str = "[fake]") -> None:
        self.db = db
        self.note = note

    def complete(
        self,
        messages: List[LLMMessage],
        *,
        output_model: Optional[Type[BaseModel]] = None,
        temperature: float = 0.2,
        **kwargs,
    ) -> str:
        if output_model is None:
            return "{}"
        import json

        return json.dumps(_fill(output_model), ensure_ascii=False)
