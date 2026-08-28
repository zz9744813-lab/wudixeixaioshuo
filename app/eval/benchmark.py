"""Benchmark harness (spec §24, §47).

Golden cases are frozen (never auto-overwritten, §47). A run answers each case
via the BenchmarkAgent and scores the prediction against the expected gold
answer: score = matched keys / total expected keys. With the deterministic
FakeProvider predictions are empty → score 0, passed False — an honest failure,
never a fabricated pass.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.eval_passes import BenchmarkAgent
from app.core.ids import new_id
from app.models.benchmark import BenchmarkCase, BenchmarkRun
from app.models.corpus import Scene


def _scene_shim(scene: Scene, question: str, expected_format: dict):
    class _Shim:
        id = scene.id
        book_id = scene.book_id
        chapter_id = scene.chapter_id
        index = scene.index
        pov = scene.pov
        time = scene.time
        location = scene.location
        participants = scene.participants
        scene_goal = question
        dominant_conflict = None
        entry_state = {"expected_format": expected_format}
        summary = question
        spans = scene.spans

    return _Shim()


def run_case(
    db: Session,
    case: BenchmarkCase,
    *,
    subject_ref: Optional[str] = None,
    provider=None,
) -> BenchmarkRun:
    scene = db.get(Scene, case.input_ref.get("scene_id"))
    if scene is None:
        raise ValueError(f"case {case.id} references a missing scene")

    agent = BenchmarkAgent(db, provider=provider)
    result = agent.run(_scene_shim(scene, case.input_ref.get("question", ""), case.expected))
    answer = result.output.answer or {}

    expected = case.expected or {}
    if expected:
        matched = sum(
            1
            for key, want in expected.items()
            if key in answer and answer[key] is not None and str(answer[key]) == str(want)
        )
        score = matched / len(expected)
        passed = matched == len(expected)
    else:
        score = 0.0
        passed = None

    run_row = BenchmarkRun(
        id=new_id("BR"),
        bench=case.bench,
        case_id=case.id,
        subject_ref=subject_ref,
        prediction=answer,
        score=score,
        metrics={"matched": score * len(expected) if expected else 0, "expected_keys": len(expected)},
        judge_model=agent.provider.name,
        passed=passed,
    )
    db.add(run_row)
    db.flush()
    return run_row


def run_bench(db: Session, bench: str, *, subject_ref: Optional[str] = None, provider=None) -> dict:
    cases = db.scalars(select(BenchmarkCase).where(BenchmarkCase.bench == bench)).all()
    if not cases:
        raise ValueError(f"no cases registered for bench {bench!r}")
    rows = [run_case(db, case, subject_ref=subject_ref, provider=provider) for case in cases]
    scored = [r.score for r in rows if r.score is not None]
    return {
        "bench": bench,
        "cases": len(rows),
        "mean_score": round(sum(scored) / len(scored), 4) if scored else 0.0,
        "passed": sum(1 for r in rows if r.passed),
        "failed": sum(1 for r in rows if r.passed is False),
        "run_ids": [r.id for r in rows],
    }


def create_case(
    db: Session,
    *,
    bench: str,
    name: str,
    scene_id: str,
    question: str,
    expected: dict,
    gold: bool = True,
) -> BenchmarkCase:
    """Register a case. Golden cases are frozen: an existing gold case with the
    same name is rejected rather than overwritten (§47)."""
    from app.models.enums import BenchName

    if gold:
        existing = db.scalars(
            select(BenchmarkCase).where(BenchmarkCase.bench == bench, BenchmarkCase.name == name)
        ).first()
        if existing is not None:
            raise ValueError(f"golden case {bench}/{name} already exists and is frozen (§47)")
    case = BenchmarkCase(
        id=new_id("BC"),
        bench=BenchName(bench),
        name=name,
        input_ref={"scene_id": scene_id, "question": question},
        expected=expected,
        gold=gold,
        frozen=True,
    )
    db.add(case)
    db.flush()
    return case
