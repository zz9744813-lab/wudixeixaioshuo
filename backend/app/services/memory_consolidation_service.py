"""
MemoryConsolidationService - 记忆固化服务 (P5)
对历史章节区间生成长期固化摘要 ConsolidatedMemory。
固化失败不阻断主流程，只记录 warning。
"""

import json
import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.memory import ChapterMemory, ConsolidatedMemory
from app.services.openai_llm_service import llm_manager
from app.utils.time_utils import utc_now

logger = logging.getLogger(__name__)


class MemoryConsolidationService:
    """记忆固化服务"""

    def __init__(self, db: Session):
        self.db = db

    async def consolidate_range(
        self,
        project_id: int,
        start_chapter: int,
        end_chapter: int,
        scope_type: str = "volume",
    ) -> dict:
        """对 [start_chapter, end_chapter] 区间章节做固化，返回固化结果字典。"""
        mems = self.db.query(ChapterMemory).filter(
            ChapterMemory.project_id == project_id,
            ChapterMemory.chapter_index >= start_chapter,
            ChapterMemory.chapter_index <= end_chapter,
        ).order_by(ChapterMemory.chapter_index.asc()).all()

        if not mems:
            return {}

        payload = await self._llm_consolidate(project_id, start_chapter, end_chapter, mems)
        if not payload:
            payload = self._fallback_consolidate(start_chapter, end_chapter, mems)

        record = self._persist(project_id, start_chapter, end_chapter, scope_type, payload)
        return {
            "id": record.id,
            "title": record.title,
            "summary": record.summary,
            "key_events": record.key_events,
            "character_arcs": record.character_arcs,
            "world_updates": record.world_updates,
            "unresolved_hooks": record.unresolved_hooks,
            "resolved_hooks": record.resolved_hooks,
            "contradictions": record.contradictions,
        }

    async def consolidate_if_needed(
        self,
        project_id: int,
        every_n_chapters: int = 10,
    ) -> dict:
        """每满 N 章固化一个区间。返回固化结果，未触发时返回 {}。"""
        max_idx = self.db.query(ChapterMemory.chapter_index).filter(
            ChapterMemory.project_id == project_id,
        ).order_by(ChapterMemory.chapter_index.desc()).first()
        if not max_idx or not max_idx[0]:
            return {}

        latest = max_idx[0]
        if latest < every_n_chapters or latest % every_n_chapters != 0:
            return {}

        start = latest - every_n_chapters + 1
        end = latest

        existing = self.db.query(ConsolidatedMemory).filter(
            ConsolidatedMemory.project_id == project_id,
            ConsolidatedMemory.scope_start_chapter == start,
            ConsolidatedMemory.scope_end_chapter == end,
        ).first()
        if existing:
            return {}

        return await self.consolidate_range(project_id, start, end)

    async def detect_character_conflicts(
        self,
        project_id: int,
        start_chapter: int,
        end_chapter: int,
    ) -> List[dict]:
        """检测区间内角色设定/状态矛盾（粗粒度，基于章节记忆的 character_changes）。"""
        mems = self.db.query(ChapterMemory).filter(
            ChapterMemory.project_id == project_id,
            ChapterMemory.chapter_index >= start_chapter,
            ChapterMemory.chapter_index <= end_chapter,
        ).all()

        seen = {}
        conflicts = []
        for m in mems:
            for change in (m.character_changes or []):
                if not isinstance(change, dict):
                    continue
                name = change.get("name")
                state = change.get("state") or change.get("change")
                if not name or not state:
                    continue
                if name in seen and seen[name] != state and {seen[name], state} == {"死亡", "存活"}:
                    conflicts.append({
                        "character": name,
                        "previous": seen[name],
                        "current": state,
                        "chapter_index": m.chapter_index,
                    })
                seen[name] = state
        return conflicts

    async def _llm_consolidate(self, project_id, start, end, mems) -> Optional[dict]:
        summaries = "\n".join(
            f"第{m.chapter_index}章：{m.short_summary or ''}" for m in mems
        )[:6000]
        prompt = (
            "你是小说长期记忆固化助手。请把以下章节区间压缩为一份长期固化记忆，"
            "输出严格 JSON（不要解释）。\n\n"
            f"章节区间：第{start}章 - 第{end}章\n"
            f"章节摘要：\n{summaries}\n\n"
            "输出结构：\n"
            "{\n"
            '  "title": "",\n'
            '  "summary": "",\n'
            '  "key_events": [],\n'
            '  "character_arcs": {},\n'
            '  "world_updates": [],\n'
            '  "unresolved_hooks": [],\n'
            '  "resolved_hooks": [],\n'
            '  "contradictions": []\n'
            "}"
        )
        try:
            response = await llm_manager.generate(
                prompt=prompt,
                role="memory_update",
                temperature=0.4,
                db=self.db,
                request_type="memory_consolidation",
                project_id=project_id,
            )
            return self._parse_json(response.get("content", ""))
        except Exception as e:
            logger.warning(f"记忆固化 LLM 调用失败: {e}")
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

    def _fallback_consolidate(self, start, end, mems) -> dict:
        key_events = []
        unresolved = []
        for m in mems:
            key_events.extend(m.key_events or [])
            unresolved.extend(m.unresolved_questions or [])
        return {
            "title": f"第{start}-{end}章 固化记忆",
            "summary": "；".join(
                (m.short_summary or "") for m in mems if m.short_summary
            )[:2000],
            "key_events": key_events[:30],
            "character_arcs": {},
            "world_updates": [],
            "unresolved_hooks": list(dict.fromkeys(unresolved))[:20],
            "resolved_hooks": [],
            "contradictions": [],
        }

    def _persist(self, project_id, start, end, scope_type, payload) -> ConsolidatedMemory:
        record = ConsolidatedMemory(
            project_id=project_id,
            scope_type=scope_type,
            scope_start_chapter=start,
            scope_end_chapter=end,
            title=payload.get("title") or f"第{start}-{end}章 固化记忆",
            summary=payload.get("summary") or "",
            key_events=payload.get("key_events") or [],
            character_arcs=payload.get("character_arcs") or {},
            world_updates=payload.get("world_updates") or [],
            unresolved_hooks=payload.get("unresolved_hooks") or [],
            resolved_hooks=payload.get("resolved_hooks") or [],
            contradictions=payload.get("contradictions") or [],
            embedding_text=(payload.get("summary") or "")[:1000],
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record
