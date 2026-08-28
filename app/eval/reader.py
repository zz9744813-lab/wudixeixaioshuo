"""Reader Simulator service (spec §21).

Runs a ReaderProfile-weighted simulation over a text (or an ingested Scene) and
persists the result as a ``reader_sim`` Evaluation plus an Artifact.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.agents.eval_passes import ReaderAgent
from app.core.ids import new_id
from app.models.corpus import Scene
from app.models.enums import ArtifactType, EvaluationType
from app.models.evaluation import Evaluation, ReaderProfile
from app.models.research import Artifact


class _TextShim:
    """Scene-like shim carrying raw text (spans empty -> summary is used)."""

    def __init__(self, text: str, profile: Optional[ReaderProfile]) -> None:
        self.id = "READER-SIM"
        self.book_id = "evaluation"
        self.chapter_id = "reader_sim"
        self.index = 0
        self.pov = None
        self.time = None
        self.location = None
        self.participants = []
        self.scene_goal = None
        self.dominant_conflict = None
        self.entry_state = dict(profile.metadata_ or {}) if profile else {}
        if profile is not None:
            self.entry_state.update(
                {
                    "patience": profile.patience,
                    "pacing_preference": profile.pacing_preference,
                    "novelty_preference": profile.novelty_preference,
                    "logic_sensitivity": profile.logic_sensitivity,
                    "romance_weight": profile.romance_weight,
                    "suspense_weight": profile.suspense_weight,
                    "action_weight": profile.action_weight,
                    "erotic_tension_weight": profile.erotic_tension_weight,
                    "tolerance_for_repetition": profile.tolerance_for_repetition,
                    "tolerance_for_coincidence": profile.tolerance_for_coincidence,
                    "tolerance_for_exposition": profile.tolerance_for_exposition,
                    "cliffhanger_preference": profile.cliffhanger_preference,
                }
            )
        self.summary = text
        self.spans = []


def simulate_reader(
    db: Session,
    text: str,
    profile: Optional[ReaderProfile] = None,
    *,
    provider=None,
    scene: Optional[Scene] = None,
) -> Evaluation:
    """Simulate a reader over ``text`` (or a Scene's own text)."""
    if scene is not None:
        text = "\n".join(s.text for s in scene.spans) or (scene.summary or "")
    agent = ReaderAgent(db, provider=provider)
    result = agent.run(_TextShim(text, profile))
    out = result.output

    evaluation = Evaluation(
        id=new_id("EVAL"),
        type=EvaluationType.READER_SIM,
        subject_a_ref=profile.id if profile else None,
        winner=None,
        confidence=result.confidence,
        metrics=out.model_dump(),
        judge_model=agent.provider.name,
        blind=True,
    )
    db.add(evaluation)
    db.add(
        Artifact(
            id=new_id("ART"),
            type=ArtifactType.REPORT,
            parent_type="reader_sim",
            parent_id=evaluation.id,
            payload={"text_chars": len(text), "reader": out.model_dump(), "run_id": result.run_id},
            source_class="ai_generated",
        )
    )
    db.flush()
    return evaluation
