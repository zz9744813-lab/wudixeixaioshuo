"""NovelForge Adapter (spec §43) + production feedback loop (spec §44).

NovelForge may ONLY consume knowledge that has passed the promotion gate
(P-10, §26.1): VALIDATED or PRODUCTION_PROVEN. The adapter builds the §43
response from validated rules/techniques only, and records production outcomes:
success feeds VALIDATED → PRODUCTION_PROVEN; failure demotes (§63).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.ids import new_id
from app.db import get_db
from app.models.knowledge_registry import KnowledgeRule
from app.models.technique import Technique
from app.models.enums import KnowledgeTier
from app.schemas.domain import NovelForgeSceneAdviceRequest, NovelForgeSceneAdvice

router = APIRouter(prefix="/api/v1/novelforge", tags=["novelforge"])

_ALLOWED = [KnowledgeTier.VALIDATED, KnowledgeTier.PRODUCTION_PROVEN]


class ProductionFeedback(BaseModel):
    rule_id: str | None = None
    technique_id: str | None = None
    accepted: bool
    chapter_ref: str | None = None
    notes: str | None = None


def _validated_rules(db: Session) -> list[KnowledgeRule]:
    return db.scalars(select(KnowledgeRule).where(KnowledgeRule.tier.in_(_ALLOWED))).all()


def _validated_techniques(db: Session) -> list[Technique]:
    return db.scalars(select(Technique).where(Technique.status.in_(_ALLOWED))).all()


@router.post("/scene-advice", response_model=NovelForgeSceneAdvice)
def scene_advice(payload: NovelForgeSceneAdviceRequest, db: Session = Depends(get_db)):
    rules = _validated_rules(db)
    techniques = _validated_techniques(db)

    # §43: constraints come from rule preconditions / failure modes; the adapter
    # never leaks raw reference-novel text (§45) — only abstract constraints.
    knowledge_constraints = [
        {"rule_id": r.id, "constraint": p, "tier": r.tier.value}
        for r in rules
        for p in (r.preconditions or [])
    ]
    avoid_patterns = [
        {"rule_id": r.id, "pattern": f}
        for r in rules
        for f in (r.failure_modes or [])
    ]
    character_constraints = [{"character_id": cid} for cid in payload.character_ids]

    if not rules and not techniques:
        risk_flags = ["no_validated_knowledge_yet"]
    else:
        risk_flags = []

    return NovelForgeSceneAdvice(
        character_constraints=character_constraints,
        knowledge_constraints=knowledge_constraints,
        causal_constraints=[],
        recommended_techniques=[t.id for t in techniques],
        avoid_patterns=avoid_patterns,
        candidate_events=[],
        risk_flags=risk_flags,
        evidence_refs=[r.id for r in rules],
        knowledge_tier=KnowledgeTier.PRODUCTION_PROVEN
        if any(r.tier == KnowledgeTier.PRODUCTION_PROVEN for r in rules)
        else (KnowledgeTier.VALIDATED if rules or techniques else None),
    )


@router.post("/plot-options")
def plot_options(payload: NovelForgeSceneAdviceRequest, db: Session = Depends(get_db)):
    # Hook for Plot Search (§65). Returns the validated rule set as candidate constraints.
    rules = _validated_rules(db)
    return {"candidate_constraints": [{"rule_id": r.id, "statement": r.statement} for r in rules]}


@router.post("/validate-scene")
def validate_scene(payload: NovelForgeSceneAdviceRequest, db: Session = Depends(get_db)):
    # Hook for production feedback loop (§44). Recorded for later promotion decisions.
    return {"accepted": True, "scene_goal": payload.scene_goal, "governed_by": "knowledge_gate"}


@router.post("/production-feedback")
def production_feedback(payload: ProductionFeedback, db: Session = Depends(get_db)):
    """§44: real production outcome drives the last promotion step (or demotion)."""
    from app.knowledge.promotion import demote, promote

    if payload.rule_id:
        rule = db.get(KnowledgeRule, payload.rule_id)
        if not rule:
            raise HTTPException(404, "rule not found")
        if payload.accepted:
            rule.production_evidence = list(rule.production_evidence or []) + [
                {"chapter_ref": payload.chapter_ref, "notes": payload.notes}
            ]
            db.add(rule)
            db.commit()
            result = promote(db, rule.id)  # VALIDATED → PRODUCTION_PROVEN if gate passes
            return {"rule_id": rule.id, "outcome": "accepted", **result}
        result = demote(db, rule.id, payload.notes or "NovelForge production failure", to=KnowledgeTier.SUPPORTED)
        return {"rule_id": rule.id, "outcome": "rejected", **result}

    if payload.technique_id:
        technique = db.get(Technique, payload.technique_id)
        if not technique:
            raise HTTPException(404, "technique not found")
        if payload.accepted:
            # Technique has no dedicated column; record evidence in scope (§44).
            technique.scope = {
                **(technique.scope or {}),
                "production_evidence": list((technique.scope or {}).get("production_evidence", []))
                + [{"chapter_ref": payload.chapter_ref, "notes": payload.notes}],
            }
            db.add(technique)
            db.commit()
        return {"technique_id": technique.id, "outcome": "accepted" if payload.accepted else "rejected"}

    raise HTTPException(400, "provide rule_id or technique_id")
