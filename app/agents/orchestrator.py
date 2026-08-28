"""Scene analysis orchestrator (spec §32 workflow).

Runs the multi-pass decomposition chain for one Scene in the canonical order,
each Pass as an independent Agent (spec P-12), then has the Reconciler summarize
into the Scene's canonical genome. All artifacts are written as Claims /
Events / Perceptions / ... with their ``Run`` id (never overwrite canonical
state directly, spec P-08).

Order (subset of §16 / §32 implemented so far):
Event → Perception → Knowledge → Belief → Goal → Emotion → Relationship →
Causality → TechniqueMining → CounterInterpretation → Reconcile.
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from app.agents.base import AgentRunResult
from app.agents.passes import (
    BeliefAgent,
    CausalityAgent,
    CounterInterpretationAgent,
    EmotionAgent,
    EventAgent,
    GoalAgent,
    KnowledgeAgent,
    PerceptionAgent,
    ReconcileAgent,
    RelationshipAgent,
    TechniqueAgent,
)
from app.models.corpus import Scene
from app.models.enums import TaskStatus

SCENE_PASSES = [
    EventAgent,
    PerceptionAgent,
    KnowledgeAgent,
    BeliefAgent,
    GoalAgent,
    EmotionAgent,
    RelationshipAgent,
    CausalityAgent,
    TechniqueAgent,
    CounterInterpretationAgent,
    ReconcileAgent,
]


def analyze_scene(
    db: Session, scene: Scene, provider=None, force: bool = False
) -> dict:
    if scene.analyzed and not force:
        return {"scene_id": scene.id, "skipped": True, "reason": "already analyzed"}

    passes: List[dict] = []
    reconcile: Optional[AgentRunResult] = None
    failed = 0
    for AgentCls in SCENE_PASSES:
        agent = AgentCls(db, provider=provider)
        try:
            res = agent.run(scene)
        except Exception as exc:  # noqa: BLE001 — one pass failing (network, parse,
            # provider outage) must not discard the other passes' work (§33 PARTIAL).
            failed += 1
            db.rollback()
            # Persist the failure so it is diagnosable later (spec §34, §49):
            # a FAILED run row with the error beats a silent gap.
            from app.core.ids import run_id as _rid
            from app.models.infra import Run as _Run

            db.add(
                _Run(
                    id=_rid(),
                    task_type=AgentCls.agent_type,
                    prompt_version=AgentCls.prompt_id,
                    status=TaskStatus.FAILED_RETRYABLE,
                    input_ref={"scene_id": scene.id},
                    output_ref={"error": str(exc)[:1000]},
                )
            )
            db.commit()
            passes.append({"agent": AgentCls.agent_type, "error": str(exc)[:500]})
            continue
        if isinstance(agent, ReconcileAgent):
            reconcile = res
        passes.append(
            {
                "agent": res.agent_type,
                "run_id": res.run_id,
                "model": res.model,
                "confidence": res.confidence,
                "warnings": res.warnings,
            }
        )

    # Reconciler lifts its summary into the canonical Scene genome (spec §32).
    if reconcile is not None:
        out = reconcile.output
        scene.confidence = float(getattr(out, "confidence", scene.confidence) or scene.confidence)
        if getattr(out, "summary", None):
            scene.summary = out.summary
        if not scene.exit_state:
            scene.exit_state = {"confidence": scene.confidence}

    # Scene counts as analyzed only when every pass succeeded; a PARTIAL run
    # stays re-analyzable (force=true) per the §33 state machine.
    scene.analyzed = failed == 0
    db.commit()
    return {"scene_id": scene.id, "analyzed": scene.analyzed, "failed_passes": failed, "passes": passes}
