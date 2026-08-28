"""Rollout service (spec §20).

Rolls one variant forward and stores the plan as an Artifact. The rollout is a
*plan* (state transitions, event plans, reactions, causal justifications), not
prose — prose is an optional observation layer (spec §20.2).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.agents.research_passes import RolloutAgent
from app.core.ids import new_id
from app.models.corpus import Scene
from app.models.enums import ArtifactType
from app.models.research import Artifact
from app.research.counterfactual import apply_change, build_base_state


def rollout_variant(
    db: Session,
    scene: Scene,
    changed: dict[str, Any],
    *,
    horizon_scenes: int = 3,
    parent_experiment_id: str | None = None,
    variant_label: str | None = None,
    provider=None,
) -> tuple[Artifact, Any]:
    """Build the counterfactual context for ``changed`` and roll it forward.

    Returns ``(artifact, rollout_output)``. The artifact payload records the
    base state, the applied change and the rollout steps so any conclusion can
    be traced back to its manipulation (spec §35 provenance).
    """
    base = build_base_state(scene)
    modified = apply_change(base, changed)

    agent = RolloutAgent(db, provider=provider)
    # Reuse the agent machinery by feeding the modified context as the "scene"
    # payload through a lightweight shim that exposes the fields BaseAgent reads.
    shim = _ContextShim(scene, modified, horizon_scenes)
    result = agent.run(shim)

    artifact = Artifact(
        id=new_id("ART"),
        type=ArtifactType.ROLLOUT_TREE,
        parent_type="experiment_variant" if parent_experiment_id else "scene",
        parent_id=parent_experiment_id or scene.id,
        payload={
            "variant_label": variant_label,
            "changed": changed,
            "base_state": {k: v for k, v in base.items() if k != "text"},
            "horizon_scenes": horizon_scenes,
            "rollout": result.output.model_dump(),
            "run_id": result.run_id,
            "model": result.model,
            "warnings": result.warnings,
        },
        source_class="experimental_counterfactual",
    )
    db.add(artifact)
    db.flush()
    return artifact, result.output


class _ContextShim:
    """Minimal Scene-like object so RolloutAgent sees the counterfactual context."""

    def __init__(self, scene: Scene, modified: dict, horizon: int) -> None:
        self.id = scene.id
        self.book_id = scene.book_id
        self.chapter_id = scene.chapter_id
        self.index = scene.index
        self.pov = scene.pov
        self.time = scene.time
        self.location = scene.location
        self.participants = scene.participants
        self.scene_goal = scene.scene_goal
        self.dominant_conflict = scene.dominant_conflict
        self.entry_state = modified
        self.summary = f"counterfactual horizon={horizon}"
        self.spans = scene.spans
