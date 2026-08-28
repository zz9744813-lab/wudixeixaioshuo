"""Counterfactual builder (spec §19).

Turns a declarative ``changed`` spec into a concrete modified story context,
deterministically and LLM-free. Supported operations (§19.2):

* ``remove_information``   : character no longer knows a fact
* ``knowledge_change``     : KNOWN -> SUSPECTED etc. for a character/fact
* ``relationship_change``  : move a relationship dimension for a pair
* ``trait_change``         : alter a character trait (e.g. impulsivity)
* ``stakes_change``        : raise/lower stakes of the scene goal
* ``timing_shift``         : move the reveal earlier/later by N scenes
* ``replace_choice``       : swap the character's decision branch

Everything else in the context stays FIXED (§19.1) — that is the whole point of
a controlled counterfactual.
"""
from __future__ import annotations

from typing import Any

from app.models.corpus import Scene


def build_base_state(scene: Scene) -> dict[str, Any]:
    """The FIXED baseline context of a scene (identical across variants)."""
    return {
        "book_id": scene.book_id,
        "chapter_id": scene.chapter_id,
        "scene_index": scene.index,
        "pov": scene.pov,
        "time": scene.time,
        "location": scene.location,
        "participants": list(scene.participants or []),
        "scene_goal": scene.scene_goal,
        "dominant_conflict": scene.dominant_conflict,
        "entry_state": dict(scene.entry_state or {}),
        "text": "\n".join(s.text for s in scene.spans),
    }


def apply_change(state: dict[str, Any], changed: dict[str, Any]) -> dict[str, Any]:
    """Apply one variant's ``changed`` spec to a *copy* of the base state.

    Two kinds of keys are accepted:

    * **Structured ops** (the names in ``_OPS``) perform deterministic state
      edits. A *near-miss* of an op name (e.g. ``knowledge_chg``) raises
      ``ValueError`` so a mis-specified experiment fails loudly instead of
      silently testing nothing (spec 禁止6).
    * **Free parameters** (spec §59 style, e.g. ``incremental_clues: 2``) are
      passed through verbatim as ``parameters`` so the rollout model sees the
      manipulation; they are recorded in the artifact for provenance.
    """
    out = {
        **state,
        "knowledge": {},
        "relationships": {},
        "traits": {},
        "stakes": {},
        "timing": {},
        "parameters": {},
    }
    if not changed:
        return out  # control: unchanged copy

    for op, payload in changed.items():
        if op in _OPS:
            _OPS[op](out, payload)
        else:
            import difflib

            close = difflib.get_close_matches(op, _OPS.keys(), n=1, cutoff=0.6)
            if close:
                raise ValueError(
                    f"unknown counterfactual operation: {op!r} (did you mean {close[0]!r}?)"
                )
            out["parameters"][op] = payload
    return out


def _op_remove_information(state: dict, payload: Any) -> None:
    # payload: {"character": str, "fact": str}
    state["knowledge"].setdefault(payload["character"], {})[payload["fact"]] = "UNKNOWN"


def _op_knowledge_change(state: dict, payload: Any) -> None:
    # payload: {"character": str, "fact": str, "to": KnowledgeStatus}
    state["knowledge"].setdefault(payload["character"], {})[payload["fact"]] = payload["to"]


def _op_relationship_change(state: dict, payload: Any) -> None:
    # payload: {"a": str, "b": str, "dimension": str, "value": float}
    key = f"{payload['a']}->{payload['b']}"
    state["relationships"].setdefault(key, {})[payload["dimension"]] = payload["value"]


def _op_trait_change(state: dict, payload: Any) -> None:
    # payload: {"character": str, "trait": str, "value": float}
    state["traits"].setdefault(payload["character"], {})[payload["trait"]] = payload["value"]


def _op_stakes_change(state: dict, payload: Any) -> None:
    # payload: {"level": "high"|"medium"|"low"} or {"magnitude": float}
    state["stakes"] = dict(payload)


def _op_timing_shift(state: dict, payload: Any) -> None:
    # payload: {"reveal_offset_scenes": int}  negative = earlier, positive = later
    state["timing"] = {"reveal_offset_scenes": int(payload["reveal_offset_scenes"])}


def _op_replace_choice(state: dict, payload: Any) -> None:
    # payload: {"character": str, "new_action": str}
    state["replace_choice"] = dict(payload)


_OPS = {
    "remove_information": _op_remove_information,
    "knowledge_change": _op_knowledge_change,
    "relationship_change": _op_relationship_change,
    "trait_change": _op_trait_change,
    "stakes_change": _op_stakes_change,
    "timing_shift": _op_timing_shift,
    "replace_choice": _op_replace_choice,
}
