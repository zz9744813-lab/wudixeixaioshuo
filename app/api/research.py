"""Research API: Hypothesis → Experiment → Run (spec §18–§20, §39 Research)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.ids import new_id
from app.db import get_db
from app.models.research import Hypothesis, Experiment, ExperimentVariant
from app.models.enums import VariantType
from app.schemas.domain import HypothesisCreate, HypothesisOut, ExperimentCreate, ExperimentOut

router = APIRouter(prefix="/api/v1", tags=["research"])


@router.post("/hypotheses", response_model=HypothesisOut, status_code=201)
def create_hypothesis(payload: HypothesisCreate, db: Session = Depends(get_db)):
    h = Hypothesis(
        id=new_id("H"), statement=payload.statement,
        independent_variables=payload.independent_variables,
        dependent_variables=payload.dependent_variables, controls=payload.controls,
        scope=payload.scope, expected_direction=payload.expected_direction,
        falsification_condition=payload.falsification_condition,
        origin_evidence=payload.origin_evidence,
    )
    db.add(h); db.commit(); db.refresh(h)
    return HypothesisOut(id=h.id, statement=h.statement, status=h.status, confidence=h.confidence)


@router.get("/hypotheses", response_model=list[HypothesisOut])
def list_hypotheses(db: Session = Depends(get_db)):
    rows = db.scalars(select(Hypothesis).order_by(Hypothesis.created_at.desc())).all()
    return [HypothesisOut(id=r.id, statement=r.statement, status=r.status, confidence=r.confidence) for r in rows]


@router.post("/hypotheses/{hypothesis_id}/design-experiment", response_model=ExperimentOut, status_code=201)
def design_experiment(hypothesis_id: str, payload: ExperimentCreate, db: Session = Depends(get_db)):
    h = db.get(Hypothesis, hypothesis_id)
    if not h:
        raise HTTPException(404, "hypothesis not found")
    exp = Experiment(
        id=new_id("EXP"), hypothesis_id=h.id, fixed=payload.fixed,
        measurements=payload.measurements, evaluation=payload.evaluation,
        falsification=payload.falsification,
    )
    for v in payload.variants:
        exp.variants.append(ExperimentVariant(
            id=new_id("VAR"), experiment_id=exp.id, label=v.get("label", "variant"),
            variant_type=VariantType(v.get("variant_type", "treatment")),
            changed=v.get("changed", {}), fixed=v.get("fixed", {}),
            measured=v.get("measured", {}), prompt_version=v.get("prompt_version"),
        ))
    db.add(exp); db.commit(); db.refresh(exp)
    return ExperimentOut(id=exp.id, hypothesis_id=exp.hypothesis_id, status=exp.status.value, variant_count=len(exp.variants))


@router.post("/experiments/{experiment_id}/run")
def run_experiment(experiment_id: str, db: Session = Depends(get_db)):
    exp = db.get(Experiment, experiment_id)
    if not exp:
        raise HTTPException(404, "experiment not found")
    from app.research.runner import run_experiment as execute

    try:
        return execute(db, experiment_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.get("/experiments/{experiment_id}", response_model=ExperimentOut)
def get_experiment(experiment_id: str, db: Session = Depends(get_db)):
    exp = db.get(Experiment, experiment_id)
    if not exp:
        raise HTTPException(404, "experiment not found")
    return ExperimentOut(id=exp.id, hypothesis_id=exp.hypothesis_id, status=exp.status.value, variant_count=len(exp.variants))
