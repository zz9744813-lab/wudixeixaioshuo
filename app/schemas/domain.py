"""Domain request/response DTOs for the API routers (spec §39)."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import SourceClass, KnowledgeTier, TechniqueCategory, HypothesisStatus


# ---- Corpus / Book ----
class BookCreate(BaseModel):
    title: str
    author: str | None = None
    genre: str | None = None
    corpus_source_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BookOut(BaseModel):
    id: str
    title: str
    author: str | None = None
    genre: str | None = None
    chapter_count: int = 0
    scene_count: int = 0


# ---- Scene ----
class SceneOut(BaseModel):
    id: str
    book_id: str
    chapter_id: str
    index: int
    pov: str | None = None
    location: str | None = None
    participants: list[str] = Field(default_factory=list)
    narrative_functions: list[str] = Field(default_factory=list)
    summary: str | None = None
    confidence: float = 0.0
    analyzed: bool = False


# ---- Character ----
class CharacterCreate(BaseModel):
    book_id: str
    name: str
    identity: dict[str, Any] = Field(default_factory=dict)
    background: str | None = None
    traits: list[str] = Field(default_factory=list)
    long_term_desires: list[str] = Field(default_factory=list)
    core_fears: list[str] = Field(default_factory=list)


class CharacterOut(BaseModel):
    id: str
    book_id: str
    name: str
    traits: list[str] = Field(default_factory=list)


# ---- Research ----
class HypothesisCreate(BaseModel):
    statement: str
    independent_variables: list[str] = Field(default_factory=list)
    dependent_variables: list[str] = Field(default_factory=list)
    controls: list[str] = Field(default_factory=list)
    scope: str | None = None
    expected_direction: str | None = None
    falsification_condition: str | None = None
    origin_evidence: list[dict[str, Any]] = Field(default_factory=list)


class HypothesisOut(BaseModel):
    id: str
    statement: str
    status: HypothesisStatus
    confidence: float


class ExperimentCreate(BaseModel):
    hypothesis_id: str | None = None  # taken from path; accepted but ignored if present
    fixed: dict[str, Any] = Field(default_factory=dict)
    measurements: list[str] = Field(default_factory=list)
    evaluation: dict[str, Any] = Field(default_factory=dict)
    falsification: str | None = None
    variants: list[dict[str, Any]] = Field(default_factory=list)


class ExperimentOut(BaseModel):
    id: str
    hypothesis_id: str
    status: str
    variant_count: int = 0


# ---- Knowledge ----
class TechniqueCreate(BaseModel):
    name: str
    category: TechniqueCategory
    definition: str
    mechanism: list[str] = Field(default_factory=list)
    preconditions: list[str] = Field(default_factory=list)
    failure_modes: list[str] = Field(default_factory=list)
    counterexamples: list[Any] = Field(default_factory=list)
    scope: dict[str, Any] = Field(default_factory=dict)
    status: KnowledgeTier = KnowledgeTier.OBSERVATION


class TechniqueOut(BaseModel):
    id: str
    name: str
    category: TechniqueCategory
    status: KnowledgeTier
    confidence: float


class KnowledgeRuleOut(BaseModel):
    id: str
    name: str
    tier: KnowledgeTier
    confidence: float


# ---- Ingestion (spec §6, EPIC-B) ----
class IngestResultOut(BaseModel):
    book_id: str
    source_id: str | None = None
    task_id: str
    chapter_count: int
    scene_count: int
    span_count: int
    duplicate_groups: list[list[int]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    idempotent: bool = False


# ---- NovelForge Adapter (spec §43) ----
class NovelForgeSceneAdviceRequest(BaseModel):
    story_state_id: str | None = None
    scene_goal: str
    desired_effects: dict[str, str] = Field(default_factory=dict)
    character_ids: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)


class NovelForgeSceneAdvice(BaseModel):
    character_constraints: list[dict[str, Any]] = Field(default_factory=list)
    knowledge_constraints: list[dict[str, Any]] = Field(default_factory=list)
    causal_constraints: list[dict[str, Any]] = Field(default_factory=list)
    recommended_techniques: list[str] = Field(default_factory=list)
    avoid_patterns: list[str] = Field(default_factory=list)
    candidate_events: list[dict[str, Any]] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    knowledge_tier: KnowledgeTier | None = None
