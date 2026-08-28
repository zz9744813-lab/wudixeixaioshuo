"""Evaluation Agents (EPIC-E): Reader Simulator (§21) and Benchmark QA (§24).

Their outputs are consumed by ``app.eval`` services, which persist
Evaluations/Artifacts; the agents themselves persist nothing.
"""
from __future__ import annotations

from app.agents.base import BaseAgent
from app.agents.schemas import BenchmarkPrediction, ReaderResult


class ReaderAgent(BaseAgent):
    """Simulates a reader persona reading a text (spec §21). The persona's
    weights arrive via the context package (entry_state), not a one-line prompt."""

    agent_type = "reader_sim"
    prompt_id = "eval_reader"
    output_model = ReaderResult
    persist = staticmethod(lambda db, scene, out, rid: None)


class BenchmarkAgent(BaseAgent):
    """Answers one benchmark case question about a scene (spec §24/§47)."""

    agent_type = "benchmark_qa"
    prompt_id = "eval_benchmark"
    output_model = BenchmarkPrediction
    persist = staticmethod(lambda db, scene, out, rid: None)
