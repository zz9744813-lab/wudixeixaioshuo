"""
DraftReducerService - 并行 Draft 候选选优与合并 (P7)
按加权公式从多个候选中选最佳，选择理由可追溯。
"""

import logging
from typing import List, Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class DraftReducerService:
    """并行 Draft 候选 reduce 服务"""

    def __init__(self, db: Session):
        self.db = db

    def _rank_score(self, candidate: dict) -> float:
        dims = candidate.get("score_breakdown") or {}
        overall = candidate.get("score", 0) or 0
        reader = dims.get("reader_addiction", overall)
        ending = dims.get("ending_hook", overall)
        directive = dims.get("editor_directive_fulfillment", overall)
        continuity = dims.get("continuity", overall)
        cost_penalty = min(float(candidate.get("cost", 0.0)) * 2.0, 5.0)
        return round(
            overall * 0.4
            + reader * 0.2
            + ending * 0.15
            + directive * 0.15
            + continuity * 0.1
            - cost_penalty,
            3,
        )

    async def select_best_candidate(
        self,
        project_id: int,
        chapter_id: int,
        candidates: List[dict],
        editor_directive: Optional[dict] = None,
    ) -> dict:
        """从候选中选最佳，返回 {selected, ranking, reason}。"""
        valid = [c for c in (candidates or []) if c.get("content")]
        if not valid:
            return {"selected": None, "ranking": [], "reason": "无有效候选"}

        ranked = sorted(
            valid,
            key=lambda c: self._rank_score(c),
            reverse=True,
        )
        best = ranked[0]
        ranking = [
            {
                "candidate_id": c.get("candidate_id"),
                "strategy": c.get("strategy"),
                "score": c.get("score"),
                "rank_score": self._rank_score(c),
            }
            for c in ranked
        ]
        reason = (
            f"候选 {best.get('candidate_id')}（{best.get('strategy')}）"
            f"综合排序分最高 {self._rank_score(best)}，原始评分 {best.get('score')}"
        )
        return {"selected": best, "ranking": ranking, "reason": reason}

    async def merge_candidates(
        self,
        project_id: int,
        chapter_id: int,
        candidates: List[dict],
        selected_ids: List[str],
    ) -> dict:
        """合并多个候选（MVP：拼接选中候选正文，去重空白）。"""
        chosen = [
            c for c in (candidates or [])
            if c.get("candidate_id") in set(selected_ids or [])
        ]
        if not chosen:
            return {"content": "", "merged_ids": []}
        merged = "\n\n".join(c.get("content", "") for c in chosen if c.get("content"))
        return {"content": merged, "merged_ids": [c.get("candidate_id") for c in chosen]}
