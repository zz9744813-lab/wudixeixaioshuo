"""Writer Arena (spec §22).

Round-robin blind pairwise comparison of anonymous candidates via the Judge.
Candidates may be raw texts or ingested Scenes. Aggregated win rates decide the
ranking; every pair is recorded as a ``pairwise`` Evaluation.
"""
from __future__ import annotations

from itertools import combinations
from typing import Optional

from sqlalchemy.orm import Session

from app.agents.research_passes import JudgeAgent
from app.core.ids import new_id
from app.models.corpus import Scene
from app.models.enums import ArtifactType, EvaluationType
from app.models.evaluation import Evaluation
from app.models.research import Artifact
from app.research.runner import _PairShim


def run_arena(
    db: Session,
    candidates: list[dict],
    *,
    provider=None,
) -> dict:
    """``candidates``: [{"label": str, "text": str} | {"label": str, "scene_id": str}].

    Judge sees only A/B; the mapping back to labels happens after judging.
    """
    if len(candidates) < 2:
        raise ValueError("arena needs at least 2 candidates")

    texts: dict[str, str] = {}
    for cand in candidates:
        label = cand.get("label")
        if not label:
            raise ValueError("every candidate needs a label")
        if cand.get("scene_id"):
            scene = db.get(Scene, cand["scene_id"])
            if not scene:
                raise ValueError(f"scene not found: {cand['scene_id']}")
            texts[label] = "\n".join(s.text for s in scene.spans) or (scene.summary or "")
        elif cand.get("text"):
            texts[label] = cand["text"]
        else:
            raise ValueError(f"candidate {label!r} needs text or scene_id")

    judge = JudgeAgent(db, provider=provider)
    wins: dict[str, int] = {label: 0 for label in texts}
    ties = 0
    pair_count = 0
    for label_a, label_b in combinations(sorted(texts), 2):
        result = judge.run(_TextPairShim(texts[label_a], texts[label_b]))
        out = result.output
        winner = out.winner if out.winner in ("A", "B", "TIE") else "TIE"
        if winner == "A":
            wins[label_a] += 1
        elif winner == "B":
            wins[label_b] += 1
        else:
            ties += 1
        pair_count += 1
        db.add(
            Evaluation(
                id=new_id("EVAL"),
                type=EvaluationType.PAIRWISE,
                subject_a_ref=label_a,
                subject_b_ref=label_b,
                winner=winner,
                confidence=out.confidence,
                decisive_dimensions=out.decisive_dimensions,
                evidence_spans=out.evidence_spans,
                failure_reasons=out.failure_reasons,
                metrics=out.metrics,
                judge_model=judge.provider.name,
                blind=True,
            )
        )

    ranking = sorted(wins.items(), key=lambda kv: kv[1], reverse=True)
    report = Artifact(
        id=new_id("ART"),
        type=ArtifactType.REPORT,
        parent_type="arena",
        parent_id=None,
        payload={
            "candidates": list(texts),
            "wins": wins,
            "ties": ties,
            "pairs": pair_count,
            "ranking": [label for label, _ in ranking],
            "judge_model": judge.provider.name,
        },
        source_class="ai_generated",
    )
    db.add(report)
    db.flush()
    return {
        "report_id": report.id,
        "pairs": pair_count,
        "ties": ties,
        "wins": wins,
        "ranking": [label for label, _ in ranking],
    }


class _TextPairShim(_PairShim):
    """Pair shim built from two raw texts (anonymous A/B)."""

    def __init__(self, text_a: str, text_b: str) -> None:
        self.id = "ARENA-PAIR"
        self.book_id = "arena"
        self.chapter_id = "pairwise"
        self.index = 0
        self.pov = None
        self.time = None
        self.location = None
        self.participants = []
        self.scene_goal = None
        self.dominant_conflict = None
        self.entry_state = {}
        self.summary = f"A: {text_a}\nB: {text_b}"
        self.spans = []
