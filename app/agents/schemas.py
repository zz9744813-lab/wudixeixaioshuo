"""Agent I/O contracts (spec §16 multi-pass, §31 Agent protocol).

Each PASS produces one structured output model. Fields are deliberately loose
(``str`` not enums) so the deterministic :class:`FakeProvider` can fill them and
the real model can return free-form values that a later Reconciler validates
against the controlled vocabularies (spec §5, P-03).
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class EventItem(BaseModel):
    type: str = ""
    actor: Optional[str] = None
    description: str = ""
    order_index: int = 0
    confidence: float = 0.5
    source_span: Optional[str] = None


class EventExtraction(BaseModel):
    events: List[EventItem] = Field(default_factory=list)


class PerceptionItem(BaseModel):
    character: str = ""
    perceived_event: Optional[str] = None
    content: str = ""


class PerceptionExtraction(BaseModel):
    perceptions: List[PerceptionItem] = Field(default_factory=list)


class KnowledgeItem(BaseModel):
    fact: str = ""
    character: str = ""
    status: str = "UNKNOWN"  # KnowledgeStatus vocabulary
    confidence: float = 0.5
    source_span: Optional[str] = None


class KnowledgeExtraction(BaseModel):
    updates: List[KnowledgeItem] = Field(default_factory=list)


class BeliefItem(BaseModel):
    character: str = ""
    proposition: str = ""
    probability: float = 0.5
    source: Optional[str] = None
    confidence: float = 0.5


class BeliefExtraction(BaseModel):
    beliefs: List[BeliefItem] = Field(default_factory=list)


class GoalItem(BaseModel):
    character: str = ""
    statement: str = ""
    lifecycle: str = "active"  # active|blocked|completed
    strength: float = 0.5


class GoalExtraction(BaseModel):
    goals: List[GoalItem] = Field(default_factory=list)


class EmotionItem(BaseModel):
    character: str = ""
    type: str = ""  # EmotionType vocabulary
    intensity: float = 0.5
    trigger: Optional[str] = None
    appraisal: dict = Field(default_factory=dict)
    action_tendency: dict = Field(default_factory=dict)
    evidence: List[str] = Field(default_factory=list)


class EmotionExtraction(BaseModel):
    emotions: List[EmotionItem] = Field(default_factory=list)


class RelationshipItem(BaseModel):
    source: str = ""
    target: str = ""
    dimension: str = ""  # RelationshipDimension vocabulary
    delta: float = 0.0
    cause: Optional[str] = None
    last_changed_scene: Optional[str] = None


class RelationshipExtraction(BaseModel):
    changes: List[RelationshipItem] = Field(default_factory=list)


class CausalityItem(BaseModel):
    frm: str = ""
    to: str = ""
    type: str = ""  # CausalEdgeType vocabulary
    necessity: float = 0.5
    sufficiency: float = 0.5
    confidence: float = 0.5
    evidence: List[str] = Field(default_factory=list)
    alternatives: List[str] = Field(default_factory=list)


class CausalityExtraction(BaseModel):
    edges: List[CausalityItem] = Field(default_factory=list)


class TechniqueItem(BaseModel):
    name: str = ""
    category: str = ""  # TechniqueCategory vocabulary
    mechanism: List[str] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)


class TechniqueExtraction(BaseModel):
    candidates: List[TechniqueItem] = Field(default_factory=list)


class CounterInterpretation(BaseModel):
    alternatives: List[str] = Field(default_factory=list)


class ReconcileResult(BaseModel):
    summary: str = ""
    confidence: float = 0.5
    uncertainties: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


# ---- EPIC-D: Rollout (spec §20) + Judge (spec §23) ------------------------ #
class RolloutStep(BaseModel):
    step: int = 0
    state_transition: str = ""
    event_plan: str = ""
    character_reactions: List[str] = Field(default_factory=list)
    causal_justification: str = ""


class RolloutResult(BaseModel):
    steps: List[RolloutStep] = Field(default_factory=list)
    causal_risks: List[str] = Field(default_factory=list)
    knowledge_violations: List[str] = Field(default_factory=list)


class JudgeVerdict(BaseModel):
    """Pairwise judgment. The judge never sees group labels (禁止7)."""

    winner: str = "TIE"  # A | B | TIE
    confidence: float = 0.0
    decisive_dimensions: List[str] = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict)  # dimension -> score 0..1
    evidence_spans: List[str] = Field(default_factory=list)
    failure_reasons: List[str] = Field(default_factory=list)


# ---- EPIC-E: Reader Simulator (spec §21) + Benchmark ---------------------- #
class ReaderResult(BaseModel):
    """Reader Simulator output (spec §21.2). All values 0..1."""

    continue_reading_probability: float = 0.0
    confusion: float = 0.0
    boredom: float = 0.0
    curiosity: float = 0.0
    tension: float = 0.0
    satisfaction: float = 0.0
    surprise: float = 0.0
    character_attachment: float = 0.0
    trust_in_author: float = 0.0


class BenchmarkPrediction(BaseModel):
    answer: dict = Field(default_factory=dict)
