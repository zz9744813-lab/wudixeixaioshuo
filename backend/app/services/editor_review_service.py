"""
EditorReviewService - 总编阶段性复盘 (P8)
每 N 章复盘最近章节的节奏/爽点/主线/伏笔/角色弧光，产出下一阶段调整建议。
"""

import json
import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.chapter import Chapter
from app.models.foreshadow import Foreshadow
from app.models.memory import ChapterMemory
from app.services.openai_llm_service import llm_manager

logger = logging.getLogger(__name__)


class EditorReviewService:
    """总编复盘服务"""

    def __init__(self, db: Session):
        self.db = db

    async def review_recent_chapters(
        self,
        project_id: int,
        end_chapter_index: int,
        window_size: int = 5,
    ) -> dict:
        start = max(1, end_chapter_index - window_size + 1)

        mems = self.db.query(ChapterMemory).filter(
            ChapterMemory.project_id == project_id,
            ChapterMemory.chapter_index >= start,
            ChapterMemory.chapter_index <= end_chapter_index,
        ).order_by(ChapterMemory.chapter_index.asc()).all()

        chapters = self.db.query(Chapter).filter(
            Chapter.project_id == project_id,
            Chapter.chapter_index >= start,
            Chapter.chapter_index <= end_chapter_index,
        ).order_by(Chapter.chapter_index.asc()).all()
        scores = [c.total_score for c in chapters if c.total_score]

        # 长期未回收伏笔
        stale_foreshadows = self.db.query(Foreshadow).filter(
            Foreshadow.project_id == project_id,
            Foreshadow.status.in_(["planted", "developed"]),
            Foreshadow.setup_chapter.isnot(None),
            Foreshadow.setup_chapter <= end_chapter_index - window_size,
        ).all()

        payload = await self._llm_review(
            project_id, start, end_chapter_index, mems, scores, stale_foreshadows
        )
        if not payload:
            payload = self._fallback_review(
                start, end_chapter_index, mems, scores, stale_foreshadows
            )
        payload["window"] = [start, end_chapter_index]
        return payload

    async def _llm_review(self, project_id, start, end, mems, scores, stale) -> Optional[dict]:
        summaries = "\n".join(
            f"第{m.chapter_index}章：{m.short_summary or ''}" for m in mems
        )[:4000]
        prompt = (
            "你是网文总编，请对最近章节做阶段性复盘，输出严格 JSON（不要解释）。\n\n"
            f"复盘区间：第{start}-{end}章\n"
            f"章节摘要：\n{summaries}\n"
            f"近期评分：{scores}\n"
            f"长期未回收伏笔：{[f.title for f in stale]}\n\n"
            "输出结构：\n"
            "{\n"
            '  "summary": "",\n'
            '  "tension_analysis": {"is_flat": false, "reason": ""},\n'
            '  "plotline_status": [],\n'
            '  "foreshadow_status": [],\n'
            '  "character_arc_status": {},\n'
            '  "next_adjustments": []\n'
            "}"
        )
        try:
            response = await llm_manager.generate(
                prompt=prompt,
                role="planner",
                temperature=0.5,
                db=self.db,
                request_type="editor_review",
                project_id=project_id,
            )
            return self._parse_json(response.get("content", ""))
        except Exception as e:
            logger.warning(f"总编复盘 LLM 调用失败: {e}")
            return None

    def _parse_json(self, content: str) -> Optional[dict]:
        if not content:
            return None
        text = content.strip()
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return None
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            return None

    def _fallback_review(self, start, end, mems, scores, stale) -> dict:
        avg = round(sum(scores) / len(scores), 1) if scores else None
        is_flat = bool(avg is not None and avg < 75)
        adjustments = []
        if is_flat:
            adjustments.append(f"第{end + 1}章必须加入一次中型反转，提升张力")
        if stale:
            adjustments.append(
                f"尽快回收长期伏笔：{('、'.join(f.title for f in stale[:3]))}"
            )
        if not adjustments:
            adjustments.append(f"保持当前节奏，第{end + 1}章继续推进主线")
        return {
            "summary": "；".join((m.short_summary or "") for m in mems if m.short_summary)[:1000],
            "tension_analysis": {
                "is_flat": is_flat,
                "reason": f"近{len(scores)}章均分 {avg}" if avg is not None else "样本不足",
            },
            "plotline_status": [],
            "foreshadow_status": [
                {"id": f.id, "title": f.title, "status": f.status} for f in stale
            ],
            "character_arc_status": {},
            "next_adjustments": adjustments,
        }
