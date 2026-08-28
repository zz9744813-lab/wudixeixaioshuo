"""Concrete analysis Passes (spec §16 PASS-xx).

Each Pass is an independent Agent (spec P-12) that extracts one kind of artifact
from a Scene and persists it with the run id. The orchestrator
(:mod:`app.agents.orchestrator`) runs them in the canonical order from §32.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents.base import BaseAgent
from app.agents.schemas import (
    BeliefExtraction,
    CausalityExtraction,
    CounterInterpretation,
    EmotionExtraction,
    EventExtraction,
    GoalExtraction,
    KnowledgeExtraction,
    PerceptionExtraction,
    ReconcileResult,
    RelationshipExtraction,
    TechniqueExtraction,
)
from app.core.ids import new_id
from app.models.character import Character
from app.models.corpus import Scene
from app.models.decomposition import BeliefState, Event, Goal, Perception
from app.models.emotion import EmotionState
from app.models.relationship import RelationshipState
from app.models.claims import Claim


# ---- persist callbacks (write artifacts, never canonical state directly) -- #
def _persist_events(db: Session, scene: Scene, out: EventExtraction, run_id: str) -> None:
    for i, e in enumerate(out.events):
        db.add(
            Event(
                id=new_id("EVT"),
                scene_id=scene.id,
                book_id=scene.book_id,
                actor_id=None,
                types=[e.type] if e.type else [],
                description=e.description or "(unspecified)",
                order_index=e.order_index or i,
                confidence=e.confidence,
                source_span_id=e.source_span,
            )
        )


def _persist_perceptions(db: Session, scene: Scene, out: PerceptionExtraction, run_id: str) -> None:
    for p in out.perceptions:
        db.add(
            Perception(
                id=new_id("PER"),
                scene_id=scene.id,
                character_id=_character_id(db, scene.book_id, p.character),
                perceived_event_id=None,
                content=p.content or "(unspecified)",
                confidence=0.5,
            )
        )


def _persist_knowledge(db: Session, scene: Scene, out: KnowledgeExtraction, run_id: str) -> None:
    # Knowledge updates are Claims until reconciled (spec P-08); persist as Claims.
    for k in out.updates:
        db.add(
            Claim(
                id=new_id("CLM"),
                subject=k.fact or "(unspecified)",
                predicate=f"knowledge:{k.status}",
                object=k.character,
                confidence=k.confidence,
                agent_run=run_id,
                evidence=[{"span": k.source_span}] if k.source_span else [],
            )
        )


def _persist_beliefs(db: Session, scene: Scene, out: BeliefExtraction, run_id: str) -> None:
    for b in out.beliefs:
        db.add(
            BeliefState(
                id=new_id("BLF"),
                character_id=_character_id(db, scene.book_id, b.character),
                scene_id=scene.id,
                proposition=b.proposition or "(unspecified)",
                probability=b.probability,
                source=b.source,
                confidence=b.confidence,
            )
        )


def _persist_goals(db: Session, scene: Scene, out: GoalExtraction, run_id: str) -> None:
    for g in out.goals:
        db.add(
            Goal(
                id=new_id("GOAL"),
                character_id=_character_id(db, scene.book_id, g.character),
                scene_id=scene.id,
                statement=g.statement or "(unspecified)",
                lifecycle=g.lifecycle,
                strength=g.strength,
            )
        )


def _persist_emotions(db: Session, scene: Scene, out: EmotionExtraction, run_id: str) -> None:
    for em in out.emotions:
        db.add(
            EmotionState(
                id=new_id("EMO"),
                character_id=_character_id(db, scene.book_id, em.character),
                scene_id=scene.id,
                emotion=em.type or "unknown",
                intensity=em.intensity,
                trigger_event=None,
                appraisal=em.appraisal,
                action_tendency=em.action_tendency,
                evidence=em.evidence,
                confidence=0.5,
            )
        )


def _persist_relationships(db: Session, scene: Scene, out: RelationshipExtraction, run_id: str) -> None:
    for r in out.changes:
        db.add(
            RelationshipState(
                id=new_id("REL"),
                character_a_id=_character_id(db, scene.book_id, r.source),
                character_b_id=_character_id(db, scene.book_id, r.target),
                dimension=r.dimension or "trust",
                value=r.delta,
                confidence=0.5,
                cause=r.cause,
                last_changed_scene=scene.id,
            )
        )


def _persist_causality(db: Session, scene: Scene, out: CausalityExtraction, run_id: str) -> None:
    for c in out.edges:
        db.add(
            Claim(
                id=new_id("CLM"),
                subject=c.frm or "(event)",
                predicate=f"causes:{c.type}",
                object=c.to or "(event)",
                confidence=c.confidence,
                agent_run=run_id,
                evidence=[{"text": t} for t in c.evidence],
            )
        )


def _persist_techniques(db: Session, scene: Scene, out: TechniqueExtraction, run_id: str) -> None:
    for t in out.candidates:
        db.add(
            Claim(
                id=new_id("CLM"),
                subject=t.name or "(technique)",
                predicate="technique:candidate",
                object=t.category,
                confidence=0.4,
                agent_run=run_id,
                evidence=[{"text": e} for e in t.evidence],
            )
        )


def _persist_counter(db: Session, scene: Scene, out: CounterInterpretation, run_id: str) -> None:
    for alt in out.alternatives:
        db.add(
            Claim(
                id=new_id("CLM"),
                subject=scene.id,
                predicate="counterinterpretation",
                object=alt,
                confidence=0.3,
                agent_run=run_id,
                evidence=[],
            )
        )


def _character_id(db: Session, book_id: str, name: str | None):
    if not name:
        return None
    existing = db.query(Character).filter(Character.book_id == book_id, Character.name == name).first()
    if existing:
        return existing.id
    ch = Character(id=new_id("CHAR"), book_id=book_id, name=name)
    db.add(ch)
    db.flush()
    return ch.id


# ---- Agent classes ------------------------------------------------------- #
class EventAgent(BaseAgent):
    agent_type = "event"
    prompt_id = "scene_event"
    output_model = EventExtraction
    persist = staticmethod(_persist_events)


class PerceptionAgent(BaseAgent):
    agent_type = "perception"
    prompt_id = "scene_perception"
    output_model = PerceptionExtraction
    persist = staticmethod(_persist_perceptions)


class KnowledgeAgent(BaseAgent):
    agent_type = "knowledge"
    prompt_id = "scene_knowledge"
    output_model = KnowledgeExtraction
    persist = staticmethod(_persist_knowledge)


class BeliefAgent(BaseAgent):
    agent_type = "belief"
    prompt_id = "scene_belief"
    output_model = BeliefExtraction
    persist = staticmethod(_persist_beliefs)


class GoalAgent(BaseAgent):
    agent_type = "goal"
    prompt_id = "scene_goal"
    output_model = GoalExtraction
    persist = staticmethod(_persist_goals)


class EmotionAgent(BaseAgent):
    agent_type = "emotion"
    prompt_id = "scene_emotion"
    output_model = EmotionExtraction
    persist = staticmethod(_persist_emotions)


class RelationshipAgent(BaseAgent):
    agent_type = "relationship"
    prompt_id = "scene_relationship"
    output_model = RelationshipExtraction
    persist = staticmethod(_persist_relationships)


class CausalityAgent(BaseAgent):
    agent_type = "causality"
    prompt_id = "scene_causality"
    output_model = CausalityExtraction
    persist = staticmethod(_persist_causality)


class TechniqueAgent(BaseAgent):
    agent_type = "technique"
    prompt_id = "scene_technique"
    output_model = TechniqueExtraction
    persist = staticmethod(_persist_techniques)


class CounterInterpretationAgent(BaseAgent):
    agent_type = "counterinterpretation"
    prompt_id = "scene_counterinterpretation"
    output_model = CounterInterpretation
    persist = staticmethod(_persist_counter)


class ReconcileAgent(BaseAgent):
    agent_type = "reconcile"
    prompt_id = "scene_reconcile"
    output_model = ReconcileResult
    persist = staticmethod(lambda db, scene, out, rid: None)
