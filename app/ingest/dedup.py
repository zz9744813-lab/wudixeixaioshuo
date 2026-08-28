"""Duplicate detection (spec §6.2, §36).

Detects exact-duplicate Scenes (identical normalized text) and near-duplicate
Scenes (high shingle/Jaccard overlap). The ingest service reports these groups so
operators can decide whether a repeat is intentional (e.g. a refrain) or a
processing artifact — the detector never deletes data, it only surfaces evidence
(spec P-03 / P-06).
"""
from __future__ import annotations

import hashlib
import re
from typing import Dict, List

_NORMALIZE = re.compile(r"\s+")

NEAR_DUP_THRESHOLD = 0.85
_SHINGLE_SIZE = 5


def _fingerprint(text: str) -> str:
    norm = _NORMALIZE.sub(" ", text).strip().lower()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def _shingles(text: str) -> frozenset:
    norm = _NORMALIZE.sub(" ", text).strip().lower()
    tokens = norm.split()
    if len(tokens) <= _SHINGLE_SIZE:
        return frozenset([" ".join(tokens)]) if tokens else frozenset()
    return frozenset(
        " ".join(tokens[i : i + _SHINGLE_SIZE]) for i in range(len(tokens) - _SHINGLE_SIZE + 1)
    )


def find_duplicates(scene_texts: List[str]) -> List[List[int]]:
    """Return groups of scene *indices* that are exact or near duplicates.

    Exact duplicates (same fingerprint) are always grouped. Near duplicates
    (Jaccard >= threshold on word-shingles) are grouped when both scenes are long
    enough to make the overlap meaningful (short scenes collide too easily).
    """
    n = len(scene_texts)
    fps: List[str] = [_fingerprint(t) for t in scene_texts]
    shingles: List[frozenset] = [_shingles(t) for t in scene_texts]
    lengths: List[int] = [len(_NORMALIZE.sub(" ", t).strip()) for t in scene_texts]

    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i in range(n):
        for j in range(i + 1, n):
            if fps[i] == fps[j]:
                union(i, j)
                continue
            if lengths[i] < 120 or lengths[j] < 120:
                continue  # too short to judge near-dup reliably
            sa, sb = shingles[i], shingles[j]
            if not sa or not sb:
                continue
            inter = len(sa & sb)
            union_size = len(sa | sb)
            if union_size and inter / union_size >= NEAR_DUP_THRESHOLD:
                union(i, j)

    groups: Dict[int, List[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return [sorted(g) for g in groups.values() if len(g) > 1]
