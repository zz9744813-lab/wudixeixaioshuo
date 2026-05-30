"""
BookStateService - 全书状态管理 (P2)
从已完成章节的记忆/伏笔聚合出全书状态，供总编 Agent 决策。
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.chapter import Chapter, ChapterStatus
from app.models.editor import BookState
from app.models.foreshadow import Foreshadow
from app.models.memory import ChapterMemory
from app.utils.time_utils import utc_now

logger = logging.getLogger(__name__)


class BookStateService:
    """全书状态服务"""

    def __init__(self, db: Session):
        self.db = db

    async def get_or_create_state(self, project_id: int) -> BookState:
        state = self.db.query(BookState).filter(
            BookState.project_id == project_id
        ).first()
        if state:
            return state
        state = BookState(project_id=project_id)
        self.db.add(state)
        self.db.commit()
        self.db.refresh(state)
        return state

    async def update_from_completed_chapter(
        self, project_id: int, chapter_id: int
    ) -> BookState:
        """章节完成后增量更新全书状态"""
        state = await self.get_or_create_state(project_id)

        mem = self.db.query(ChapterMemory).filter(
            ChapterMemory.chapter_id == chapter_id
        ).first()

        if mem:
            # 累加张力曲线点（用关键事件数量做粗略张力近似）
            tension = list(state.tension_curve or [])
            tension.append({
                "chapter_index": mem.chapter_index,
                "events": len(mem.key_events or []),
            })
            state.tension_curve = tension

            # 合并未解之谜为未决冲突
            unresolved = list(state.unresolved_conflicts or [])
            for q in (mem.unresolved_questions or []):
                if q not in unresolved:
                    unresolved.append(q)
            state.unresolved_conflicts = unresolved

            if mem.chapter_index and mem.chapter_index > (state.last_analyzed_chapter_index or 0):
                state.last_analyzed_chapter_index = mem.chapter_index
            if mem.short_summary:
                state.summary = mem.short_summary

        # 刷新活跃伏笔与待回收候选
        self._refresh_foreshadows(state, project_id)

        state.updated_at = utc_now()
        self.db.commit()
        self.db.refresh(state)
        return state

    async def rebuild_state(self, project_id: int) -> BookState:
        """从全部已完成章节重建全书状态"""
        state = await self.get_or_create_state(project_id)
        state.tension_curve = []
        state.unresolved_conflicts = []
        state.last_analyzed_chapter_index = 0
        state.summary = None
        self.db.commit()

        completed = self.db.query(Chapter).filter(
            Chapter.project_id == project_id,
            Chapter.status == ChapterStatus.COMPLETED,
        ).order_by(Chapter.chapter_index.asc()).all()

        for chapter in completed:
            await self.update_from_completed_chapter(project_id, chapter.id)

        return await self.get_or_create_state(project_id)

    def _refresh_foreshadows(self, state: BookState, project_id: int):
        active_statuses = ["planted", "developed", "ready_to_payoff"]
        active = self.db.query(Foreshadow).filter(
            Foreshadow.project_id == project_id,
            Foreshadow.status.in_(active_statuses),
        ).all()
        state.active_foreshadows = [
            {"id": f.id, "title": f.title, "status": f.status}
            for f in active
        ]
        state.next_payoff_candidates = [
            {"id": f.id, "title": f.title}
            for f in active
            if f.status == "ready_to_payoff"
        ]
