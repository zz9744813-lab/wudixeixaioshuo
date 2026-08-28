"""Research layer (EPIC-D, spec §18–§20).

Deterministic counterfactual construction + LLM rollout + controlled experiment
execution with blind pairwise judging. A re-run with identical inputs is
idempotent at the Task level; experiment conclusions always come from measured
comparisons against a control, never from the proposing agent (spec P-08).
"""
