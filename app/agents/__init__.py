"""Analysis agents (EPIC-C, spec §16/§32).

Multi-pass decomposition of a Scene into Events / Perceptions / Knowledge /
Belief / Goal / Emotion / Relationship / Causality / Techniques, plus
counter-interpretation and reconciliation. Each pass is an independent Agent that
records a Run + ModelCall for provenance (spec §35).
"""
from __future__ import annotations

from app.agents.base import AgentRunResult, BaseAgent
from app.agents.orchestrator import SCENE_PASSES, analyze_scene
from app.agents.passes import (
    BeliefAgent,
    CausalityAgent,
    CounterInterpretationAgent,
    EmotionAgent,
    EventAgent,
    GoalAgent,
    KnowledgeAgent,
    PerceptionAgent,
    ReconcileAgent,
    RelationshipAgent,
    TechniqueAgent,
)
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

__all__ = [
    "BaseAgent",
    "AgentRunResult",
    "analyze_scene",
    "SCENE_PASSES",
    "EventAgent",
    "PerceptionAgent",
    "KnowledgeAgent",
    "BeliefAgent",
    "GoalAgent",
    "EmotionAgent",
    "RelationshipAgent",
    "CausalityAgent",
    "TechniqueAgent",
    "CounterInterpretationAgent",
    "ReconcileAgent",
    "EventExtraction",
    "PerceptionExtraction",
    "KnowledgeExtraction",
    "BeliefExtraction",
    "GoalExtraction",
    "EmotionExtraction",
    "RelationshipExtraction",
    "CausalityExtraction",
    "TechniqueExtraction",
    "CounterInterpretation",
    "ReconcileResult",
]
