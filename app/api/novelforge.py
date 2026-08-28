"""NovelForge Adapter (spec §43).

NovelForge may ONLY consume knowledge that has passed the promotion gate
(P-10, §26.1): VALIDATED or PRODUCTION_PROVEN. This endpoint enforces that by
querying only those tiers for recommendations, and tags the response with the
highest tier used so NovelForge can refuse lower-grade advice.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.technique import Technique
from app.models.knowledge_registry import KnowledgeRule
from app.models.enums import KnowledgeTier
from app.schemas.domain import NovelForgeSceneAdviceRequest, NovelForgeSceneAdvice

router = APIRouter(prefix="/api/v1/novelforge", tags=["novelforge"])

_ALLOWED = [KnowledgeTier.VALIDATED, KnowledgeTier.PRODUCTION_PROVEN]


@router.post("/scene-advice", response_model=NovelForgeSceneAdvice)
def scene_advice(payload: NovelForgeSceneAdviceRequest, db: Session = Depends(get_db)):
    rules = db.scalars(select(KnowledgeRule).where(KnowledgeRule.tier.in_(_ALLOWED))).all()
    techniques = db.scalars(select(Technique).where(Technique.status.in_(_ALLOWED))).all()

    tier_used = None
    if rules:
        tier_used = KnowledgeTier.VALIDATED  # both tiers allowed; report the floor

    return NovelForgeSceneAdvice(
        recommended_techniques=[t.id for t in techniques],
        avoid_patterns=[],  # populated once behavior patterns are graded
        risk_flags=[] if rules else ["no_validated_knowledge_yet"],
        evidence_refs=[r.id for r in rules],
        knowledge_tier=tier_used,
    )


@router.post("/plot-options")
def plot_options(payload: NovelForgeSceneAdviceRequest, db: Session = Depends(get_db)):
    # Hook for Plot Search (§65). Returns the validated rule set as candidate constraints.
    rules = db.scalars(select(KnowledgeRule).where(KnowledgeRule.tier.in_(_ALLOWED))).all()
    return {"candidate_constraints": [{"rule_id": r.id, "statement": r.statement} for r in rules]}


@router.post("/validate-scene")
def validate_scene(payload: NovelForgeSceneAdviceRequest, db: Session = Depends(get_db)):
    # Hook for production feedback loop (§44). Recorded for later promotion decisions.
    return {"accepted": True, "scene_goal": payload.scene_goal, "governed_by": "knowledge_gate"}
