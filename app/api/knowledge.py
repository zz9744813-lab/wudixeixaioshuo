"""Knowledge Layer API (spec §26, §39 Knowledge): techniques + promoted rules."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.ids import new_id
from app.db import get_db
from app.models.technique import Technique
from app.models.knowledge_registry import KnowledgeRule
from app.models.enums import KnowledgeTier
from app.schemas.domain import TechniqueCreate, TechniqueOut, KnowledgeRuleOut

router = APIRouter(prefix="/api/v1", tags=["knowledge"])


@router.post("/techniques", response_model=TechniqueOut, status_code=201)
def create_technique(payload: TechniqueCreate, db: Session = Depends(get_db)):
    t = Technique(
        id=new_id("TECH"), name=payload.name, category=payload.category,
        definition=payload.definition, mechanism=payload.mechanism,
        preconditions=payload.preconditions, failure_modes=payload.failure_modes,
        counterexamples=payload.counterexamples, scope=payload.scope, status=payload.status,
    )
    db.add(t); db.commit(); db.refresh(t)
    return TechniqueOut(id=t.id, name=t.name, category=t.category, status=t.status, confidence=t.confidence)


@router.get("/techniques", response_model=list[TechniqueOut])
def list_techniques(min_tier: str | None = None, db: Session = Depends(get_db)):
    q = select(Technique)
    if min_tier:
        # only return techniques at or above the requested promotion tier
        allowed = [t.value for t in KnowledgeTier if t.value in KnowledgeTier.__members__]
        if min_tier in allowed:
            q = q.where(Technique.status == min_tier)
    rows = db.scalars(q.order_by(Technique.confidence.desc())).all()
    return [TechniqueOut(id=r.id, name=r.name, category=r.category, status=r.status, confidence=r.confidence) for r in rows]


@router.get("/rules", response_model=list[KnowledgeRuleOut])
def list_rules(db: Session = Depends(get_db)):
    # Production may only consume VALIDATED+ rules (P-10, §26.1)
    rows = db.scalars(
        select(KnowledgeRule).where(
            KnowledgeRule.tier.in_([KnowledgeTier.VALIDATED, KnowledgeTier.PRODUCTION_PROVEN])
        )
    ).all()
    return [KnowledgeRuleOut(id=r.id, name=r.name, tier=r.tier, confidence=r.confidence) for r in rows]


@router.get("/rules/{rule_id}", response_model=KnowledgeRuleOut)
def get_rule(rule_id: str, db: Session = Depends(get_db)):
    r = db.get(KnowledgeRule, rule_id)
    if not r:
        raise HTTPException(404, "rule not found")
    return KnowledgeRuleOut(id=r.id, name=r.name, tier=r.tier, confidence=r.confidence)
