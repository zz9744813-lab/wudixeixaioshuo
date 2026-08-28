"""Scene API (spec §39 Scene). Analysis endpoint is the hook for the
multi-pass decomposition (§16/§32); here it marks the scene analyzed and
records a Run for provenance. Real Agent passes are added in later EPICs.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.ids import new_id
from app.core.run_registry import create_run, finalize_run
from app.db import get_db
from app.models.corpus import Scene
from app.models.claims import Claim, Evidence
from app.models.enums import EvidenceType, TaskStatus

router = APIRouter(prefix="/api/v1/scenes", tags=["scene"])


@router.get("/{scene_id}")
def get_scene(scene_id: str, db: Session = Depends(get_db)):
    scene = db.get(Scene, scene_id)
    if not scene:
        raise HTTPException(404, "scene not found")
    return {
        "id": scene.id,
        "book_id": scene.book_id,
        "chapter_id": scene.chapter_id,
        "index": scene.index,
        "pov": scene.pov,
        "time": scene.time,
        "location": scene.location,
        "participants": scene.participants,
        "scene_goal": scene.scene_goal,
        "dominant_conflict": scene.dominant_conflict,
        "narrative_functions": scene.narrative_functions,
        "entry_state": scene.entry_state,
        "exit_state": scene.exit_state,
        "summary": scene.summary,
        "confidence": scene.confidence,
        "genome": scene.genome,
        "analyzed": scene.analyzed,
    }


@router.get("/{scene_id}/genome")
def get_genome(scene_id: str, db: Session = Depends(get_db)):
    scene = db.get(Scene, scene_id)
    if not scene:
        raise HTTPException(404, "scene not found")
    return scene.genome or {}


@router.get("/{scene_id}/claims")
def list_claims(scene_id: str, db: Session = Depends(get_db)):
    claims = db.scalars(select(Claim).where(Claim.scope == scene_id)).all()
    return [{"id": c.id, "subject": c.subject, "predicate": c.predicate, "status": c.status} for c in claims]


@router.post("/{scene_id}/analyze")
def analyze_scene(scene_id: str, db: Session = Depends(get_db), force: bool = False):
    scene = db.get(Scene, scene_id)
    if not scene:
        raise HTTPException(404, "scene not found")
    from app.agents.orchestrator import analyze_scene as run_chain

    result = run_chain(db, scene, force=force)
    return result
