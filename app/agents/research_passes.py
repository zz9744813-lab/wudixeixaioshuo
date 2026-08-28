"""Research Agents (EPIC-D): Rollout (spec §20) and blind pairwise Judge (spec §23).

These agents do NOT persist Scene artifacts; their outputs are consumed by the
experiment runner (``app.research.runner``), which stores Artifacts/Evaluations.
"""
from __future__ import annotations

from app.agents.base import BaseAgent
from app.agents.schemas import JudgeVerdict, RolloutResult


class RolloutAgent(BaseAgent):
    """Continue a story state forward under a counterfactual change (spec §20).

    Output is a plan, not prose: per step a state transition, an event plan,
    character reactions and a causal justification (spec §20.2).
    """

    agent_type = "rollout"
    prompt_id = "research_rollout"
    output_model = RolloutResult
    persist = staticmethod(lambda db, scene, out, rid: None)


class JudgeAgent(BaseAgent):
    """Blind pairwise judge (spec §23). Receives two candidate texts labeled
    only A/B — never a model name, prompt version or group (禁止7)."""

    agent_type = "judge_pairwise"
    prompt_id = "research_judge"
    output_model = JudgeVerdict
    persist = staticmethod(lambda db, scene, out, rid: None)
