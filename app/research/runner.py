"""Experiment runner (spec §19, §23, §59).

Executes a designed experiment:

1. For every variant (control first), build the counterfactual context and roll
   it forward (``rollout_variant``).
2. Blind pairwise-judge each treatment against the control (labels stripped —
   禁止7), persisting an ``Evaluation`` per pair.
3. Aggregate per-variant mean metric, compare treatments vs control and decide
   the hypothesis outcome **against its own falsification condition** — the
   judging agent never declares success itself (spec P-08).

With the deterministic FakeProvider every metric is 0 and every verdict is TIE;
the runner then refuses to promote the hypothesis (it records a warning instead
of faking a result). A real model is required for a decisive experiment.
"""
from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from app.agents.research_passes import JudgeAgent
from app.core.ids import new_id
from app.core.run_registry import create_run, finalize_run
from app.models.enums import (
    ArtifactType,
    EvaluationType,
    ExperimentStatus,
    HypothesisStatus,
    TaskStatus,
)
from app.models.evaluation import Evaluation
from app.models.infra import DeadLetter
from app.models.research import Artifact, Experiment, Hypothesis
from app.research.rollout import rollout_variant

_DIMENSION_RE = re.compile(r"^(?P<side>a|b)\.(?P<dim>[a-z_]+)$", re.IGNORECASE)


def run_experiment(db: Session, experiment_id: str, *, provider=None, horizon_scenes: int = 3) -> dict:
    exp = db.get(Experiment, experiment_id)
    if not exp:
        raise ValueError("experiment not found")
    hyp = db.get(Hypothesis, exp.hypothesis_id)
    if not hyp:
        raise ValueError("hypothesis not found")

    # Idempotent replay (spec §33): a repeated submission returns the stored
    # verdict instead of duplicating rollouts/evaluations.
    from sqlalchemy import select

    from app.models.infra import Run

    prior = db.scalars(
        select(Run).where(Run.idempotency_key == f"exp-run:{exp.id}", Run.status == TaskStatus.SUCCESS)
    ).first()
    if prior and prior.output_ref:
        return {"experiment_id": exp.id, "idempotent": True, **prior.output_ref}

    run = create_run(db, task_type="experiment_run", idempotency_key=f"exp-run:{exp.id}")
    rid = run.id
    try:
        exp.status = ExperimentStatus.RUNNING

        # ---- 1. rollout every variant (control must be first) ------------- #
        variants = sorted(exp.variants, key=lambda v: (v.variant_type != "control", v.label))
        if not variants:
            raise ValueError("experiment has no variants")
        control = next((v for v in variants if v.variant_type == "control"), None)
        if control is None:
            # 禁止6: an experiment without a declared control is not an experiment.
            raise ValueError("experiment has no control variant (禁止6)")
        # Anchor scene: first scene of the book the hypothesis came from, or a
        # caller-provided one. We use the first scene of the book containing the
        # hypothesis' origin evidence, else any scene of the first book.
        scene = _anchor_scene(db, hyp)
        variant_outputs: dict[str, dict] = {}
        for v in variants:
            artifact, output = rollout_variant(
                db,
                scene,
                v.changed,
                horizon_scenes=horizon_scenes,
                parent_experiment_id=exp.id,
                variant_label=v.label,
                provider=provider,
            )
            variant_outputs[v.label] = {
                "artifact_id": artifact.id,
                "rollout": output.model_dump(),
            }

        # ---- 2. blind pairwise judge: each treatment vs control ----------- #
        evaluations: list[dict] = []
        for v in variants:
            if v.id == control.id:
                continue
            metrics = _judge_pair(
                db,
                control_rollout=variant_outputs[control.label]["rollout"],
                treatment_rollout=variant_outputs[v.label]["rollout"],
                control_changed=control.changed,
                treatment_changed=v.changed,
                control_label=control.label,
                treatment_label=v.label,
                provider=provider,
            )
            evaluations.append(metrics)

        # ---- 3. aggregate + decide against falsification condition -------- #
        verdict = _decide(hyp, control, evaluations)
        exp.status = ExperimentStatus.COMPLETED

        report = Artifact(
            id=new_id("ART"),
            type=ArtifactType.EXPERIMENT_REPORT,
            parent_type="experiment",
            parent_id=exp.id,
            payload={
                "hypothesis_id": hyp.id,
                "variant_outputs": variant_outputs,
                "evaluations": evaluations,
                "verdict": verdict,
            },
            source_class="experimental_counterfactual",
        )
        db.add(report)
        db.flush()

        finalize_run(db, run, TaskStatus.SUCCESS.value, output_ref={"report": report.id, **verdict})
        db.commit()
        return {
            "experiment_id": exp.id,
            "report_id": report.id,
            "status": exp.status.value,
            **verdict,
        }
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        failed = db.get(type(run), rid)
        if failed is not None:
            failed.status = TaskStatus.FAILED_RETRYABLE
        db.add(
            DeadLetter(
                id=new_id("DL"),
                original_task_id=rid,
                payload={"experiment_id": experiment_id},
                error=str(exc)[:2000],
            )
        )
        db.commit()
        raise


def _anchor_scene(db: Session, hyp: Hypothesis):
    from app.models.corpus import Scene

    scene = db.scalars(select_first_scene()).first()
    if scene is None:
        raise ValueError("no scenes ingested; cannot run an experiment")
    return scene


def select_first_scene():
    from sqlalchemy import select

    from app.models.corpus import Scene

    return select(Scene).order_by(Scene.book_id, Scene.chapter_id, Scene.index).limit(1)


def _judge_pair(
    db: Session,
    *,
    control_rollout: dict,
    treatment_rollout: dict,
    control_changed: dict,
    treatment_changed: dict,
    control_label: str,
    treatment_label: str,
    provider=None,
) -> dict:
    """Blind pairwise judge of treatment vs control. Returns the evaluation dict."""
    import json as _json

    judge = JudgeAgent(db, provider=provider)
    # Anonymous candidates: labels are A/B only (禁止7). The judge sees the two
    # rollout plans, never which group produced them.
    result = judge.run(_PairShim(control_rollout, treatment_rollout, control_changed, treatment_changed))
    out = result.output

    evaluation = Evaluation(
        id=new_id("EVAL"),
        type=EvaluationType.PAIRWISE,
        subject_a_ref=control_label,
        subject_b_ref=treatment_label,
        winner=out.winner if out.winner in ("A", "B", "TIE") else "TIE",
        confidence=out.confidence,
        decisive_dimensions=out.decisive_dimensions,
        evidence_spans=out.evidence_spans,
        failure_reasons=out.failure_reasons,
        metrics=out.metrics,
        judge_model=judge.provider.name,  # logged for audit, hidden from authors
        blind=True,
    )
    db.add(evaluation)
    db.flush()
    return {
        "evaluation_id": evaluation.id,
        "control": control_label,
        "treatment": treatment_label,
        "winner": evaluation.winner,
        "confidence": evaluation.confidence,
        "metrics": evaluation.metrics,
        "decisive_dimensions": evaluation.decisive_dimensions,
    }


class _PairShim:
    """Scene-like shim whose context carries the two anonymous rollout plans."""

    def __init__(self, control_rollout: dict, treatment_rollout: dict, control_changed: dict, treatment_changed: dict) -> None:
        import json as _json

        self.id = "PAIR"
        self.book_id = "candidates"
        self.chapter_id = "pairwise"
        self.index = 0
        self.pov = None
        self.time = None
        self.location = None
        self.participants = []
        self.scene_goal = None
        self.dominant_conflict = None
        self.entry_state = {
            "candidate_a": {"changed": control_changed},
            "candidate_b": {"changed": treatment_changed},
        }
        # Both plans are exposed under the neutral A/B labels only.
        self.summary = "A: " + _json.dumps(control_rollout, ensure_ascii=False) + "\nB: " + _json.dumps(
            treatment_rollout, ensure_ascii=False
        )
        self.spans = []


def _decide(hyp: Hypothesis, control, evaluations: list[dict]) -> dict:
    """Aggregate and decide the hypothesis outcome against its falsification.

    Honest-by-default: if the judge produced no signal at all (FakeProvider,
    all-TIE / zero metrics) we do NOT fabricate a result — the hypothesis stays
    PROPOSED with a warning (spec P-08: no self-declared success).
    """
    dims = _mean_dimensions(evaluations)
    treatment_wins = sum(1 for e in evaluations if e["winner"] == "B")
    losses = sum(1 for e in evaluations if e["winner"] == "A")
    n = len(evaluations)

    if n == 0 or not any(v > 0 for v in dims.values()):
        return {
            "hypothesis_status": HypothesisStatus.PROPOSED.value,
            "decision": "inconclusive",
            "reason": "no judge signal (deterministic provider or all-TIE); not promoted",
            "mean_dimensions": dims,
            "treatment_wins": treatment_wins,
            "control_wins": losses,
            "pairs": n,
        }

    falsified = _falsification_met(hyp.falsification_condition or "", treatment_wins, losses, n)
    if falsified:
        status = HypothesisStatus.REJECTED
    elif treatment_wins == n:
        status = HypothesisStatus.SUPPORTED
    else:
        status = HypothesisStatus.PROPOSED
    hyp.status = status
    return {
        "hypothesis_status": status.value,
        "decision": "falsified" if falsified else "supported" if status == HypothesisStatus.SUPPORTED else "partial",
        "reason": f"treatment wins {treatment_wins}/{n}",
        "mean_dimensions": dims,
        "treatment_wins": treatment_wins,
        "control_wins": losses,
        "pairs": n,
    }


def _mean_dimensions(evaluations: list[dict]) -> dict[str, float]:
    totals: dict[str, float] = {}
    counts: dict[str, int] = {}
    for e in evaluations:
        for key, val in (e.get("metrics") or {}).items():
            m = _DIMENSION_RE.match(key)
            if not m or not isinstance(val, (int, float)):
                continue
            dim = f"{m.group('side')}.{m.group('dim')}"
            totals[dim] = totals.get(dim, 0.0) + float(val)
            counts[dim] = counts.get(dim, 0) + 1
    return {k: round(v / counts[k], 4) for k, v in totals.items() if counts[k]}


def _falsification_met(condition: str, treatment_wins: int, control_wins: int, n: int) -> bool:
    """Heuristic read of the falsification condition (spec §18.1)."""
    if not condition:
        return False
    cond = condition.lower()
    if "no" in cond and ("better" in cond or "superior" in cond or "稳定优于" in condition):
        return treatment_wins == 0
    if "not stably better" in cond:
        return treatment_wins <= n // 2
    return False
