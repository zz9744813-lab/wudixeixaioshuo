"""Character API (spec §39 Character)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.ids import new_id
from app.db import get_db
from app.models.character import Character, CharacterState
from app.models.corpus import Book
from app.models.knowledge import KnowledgeState
from app.models.relationship import RelationshipState
from app.models.emotion import EmotionState
from app.schemas.domain import CharacterCreate, CharacterOut

router = APIRouter(prefix="/api/v1/characters", tags=["character"])


@router.post("", response_model=CharacterOut, status_code=201)
def create_character(payload: CharacterCreate, db: Session = Depends(get_db)):
    if not db.get(Book, payload.book_id):
        raise HTTPException(404, "book not found")
    char = Character(
        id=new_id("CHAR"),
        book_id=payload.book_id,
        name=payload.name,
        identity=payload.identity,
        background=payload.background,
        traits=payload.traits,
        long_term_desires=payload.long_term_desires,
        core_fears=payload.core_fears,
    )
    db.add(char)
    db.commit()
    db.refresh(char)
    return CharacterOut(id=char.id, book_id=char.book_id, name=char.name, traits=char.traits)


@router.get("/{character_id}", response_model=CharacterOut)
def get_character(character_id: str, db: Session = Depends(get_db)):
    char = db.get(Character, character_id)
    if not char:
        raise HTTPException(404, "character not found")
    return CharacterOut(id=char.id, book_id=char.book_id, name=char.name, traits=char.traits)


@router.get("/{character_id}/timeline")
def character_timeline(character_id: str, db: Session = Depends(get_db)):
    if not db.get(Character, character_id):
        raise HTTPException(404, "character not found")
    states = db.scalars(
        select(CharacterState).where(CharacterState.character_id == character_id)
        .order_by(CharacterState.created_at)
    ).all()
    return [
        {"scene_id": s.scene_id, "goals": s.goals, "beliefs": s.beliefs,
         "desires": s.desires, "fears": s.fears, "emotions": s.emotions,
         "confidence": s.confidence}
        for s in states
    ]


@router.get("/{character_id}/state/{scene_id}")
def character_state_at_scene(character_id: str, scene_id: str, db: Session = Depends(get_db)):
    state = db.scalars(
        select(CharacterState).where(
            CharacterState.character_id == character_id,
            CharacterState.scene_id == scene_id,
        )
    ).first()
    if not state:
        raise HTTPException(404, "no state recorded for this character at this scene")
    return {
        "character_id": character_id,
        "scene_id": scene_id,
        "goals": state.goals,
        "beliefs": state.beliefs,
        "knowledge": state.knowledge,
        "desires": state.desires,
        "fears": state.fears,
        "emotions": state.emotions,
        "commitments": state.commitments,
        "resources": state.resources,
        "constraints": state.constraints,
        "derived_from_state_id": state.derived_from_state_id,
    }
