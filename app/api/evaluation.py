"""Evaluation API (spec §39): reader profiles, reader-sim, arena, benchmarks."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.ids import new_id
from app.db import get_db
from app.eval.arena import run_arena
from app.eval.benchmark import create_case, run_bench
from app.eval.reader import simulate_reader
from app.models.corpus import Scene
from app.models.evaluation import ReaderProfile

router = APIRouter(prefix="/api/v1", tags=["evaluation"])


# ---- requests ------------------------------------------------------------- #
class ReaderProfileCreate(BaseModel):
    name: str
    patience: float = 0.5
    pacing_preference: float = 0.5
    novelty_preference: float = 0.5
    logic_sensitivity: float = 0.5
    prose_sensitivity: float = 0.5
    character_attachment_weight: float = 0.5
    romance_weight: float = 0.5
    suspense_weight: float = 0.5
    action_weight: float = 0.5
    erotic_tension_weight: float = 0.5
    tolerance_for_repetition: float = 0.5
    tolerance_for_coincidence: float = 0.5
    tolerance_for_exposition: float = 0.5
    cliffhanger_preference: float = 0.5


class ReaderSimRequest(BaseModel):
    text: str | None = None
    scene_id: str | None = None
    reader_profile_id: str | None = None


class ArenaCandidate(BaseModel):
    label: str
    text: str | None = None
    scene_id: str | None = None


class ArenaRequest(BaseModel):
    candidates: list[ArenaCandidate]


class BenchmarkCaseCreate(BaseModel):
    bench: str
    name: str
    scene_id: str
    question: str
    expected: dict = Field(default_factory=dict)
    gold: bool = True


class BenchmarkRunRequest(BaseModel):
    subject_ref: str | None = None


# ---- reader profiles ------------------------------------------------------ #
@router.post("/reader-profiles", status_code=201)
def create_reader_profile(payload: ReaderProfileCreate, db: Session = Depends(get_db)):
    profile = ReaderProfile(id=new_id("READER"), **payload.model_dump())
    db.add(profile)
    db.commit()
    return {"id": profile.id, "name": profile.name}


@router.get("/reader-profiles")
def list_reader_profiles(db: Session = Depends(get_db)):
    rows = db.scalars(select(ReaderProfile)).all()
    return [{"id": r.id, "name": r.name} for r in rows]


# ---- reader simulation ----------------------------------------------------- #
@router.post("/eval/reader-sim", status_code=201)
def reader_sim(payload: ReaderSimRequest, db: Session = Depends(get_db)):
    profile = db.get(ReaderProfile, payload.reader_profile_id) if payload.reader_profile_id else None
    if payload.scene_id:
        scene = db.get(Scene, payload.scene_id)
        if not scene:
            raise HTTPException(404, "scene not found")
        evaluation = simulate_reader(db, "", profile=profile, scene=scene)
    elif payload.text:
        evaluation = simulate_reader(db, payload.text, profile=profile)
    else:
        raise HTTPException(400, "provide text or scene_id")
    db.commit()
    return {"evaluation_id": evaluation.id, "metrics": evaluation.metrics, "judge_model": evaluation.judge_model}


# ---- arena ----------------------------------------------------------------- #
@router.post("/arena/run", status_code=201)
def arena(payload: ArenaRequest, db: Session = Depends(get_db)):
    try:
        result = run_arena(db, [c.model_dump() for c in payload.candidates])
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    db.commit()
    return result


# ---- benchmarks ------------------------------------------------------------ #
@router.post("/benchmarks/cases", status_code=201)
def add_benchmark_case(payload: BenchmarkCaseCreate, db: Session = Depends(get_db)):
    try:
        case = create_case(
            db,
            bench=payload.bench,
            name=payload.name,
            scene_id=payload.scene_id,
            question=payload.question,
            expected=payload.expected,
            gold=payload.gold,
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    db.commit()
    return {"id": case.id, "bench": case.bench, "name": case.name, "gold": case.gold}


@router.post("/benchmarks/{bench}/run")
def run_benchmark(bench: str, payload: BenchmarkRunRequest, db: Session = Depends(get_db)):
    try:
        result = run_bench(db, bench, subject_ref=payload.subject_ref)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    db.commit()
    return result
