"""Evaluation layer (EPIC-E, spec §21–§24): Reader Simulator, Arena, Benchmark.

Blind by construction: judges and readers never see group labels, model names or
prompt versions (禁止7, §22.1); provenance is stored separately on the
Evaluation row (judge_model) for audit only.
"""
