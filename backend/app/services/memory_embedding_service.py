"""
MemoryEmbeddingService - 记忆向量生成与回填 (P4)
embedding 失败不阻断主流程，只记录 warning。
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.memory import (
    CharacterMemory,
    ChapterMemory,
    RelationshipMemory,
    WorldMemory,
)
from app.services.embedding_service import EmbeddingService
from app.utils.time_utils import utc_now

logger = logging.getLogger(__name__)

_MODEL_MAP = {
    "chapter": ChapterMemory,
    "character": CharacterMemory,
    "world": WorldMemory,
    "relationship": RelationshipMemory,
}


class MemoryEmbeddingService:
    """记忆向量生成与回填"""

    def __init__(self, db: Session):
        self.db = db
        self.embedding_service = EmbeddingService(db)

    def build_chapter_embedding_text(self, memory: ChapterMemory) -> str:
        parts = [
            f"第{memory.chapter_index}章" if memory.chapter_index else "",
            memory.short_summary or "",
            "关键事件：" + "；".join(map(str, memory.key_events or [])),
            "未解之谜：" + "；".join(map(str, memory.unresolved_questions or [])),
        ]
        return "\n".join(p for p in parts if p).strip()

    def build_character_embedding_text(self, memory: CharacterMemory) -> str:
        parts = [
            f"角色：{memory.name}",
            f"定位：{memory.role_type or ''}",
            memory.summary or "",
            "目标：" + "；".join(map(str, memory.goals or [])),
        ]
        return "\n".join(p for p in parts if p).strip()

    def build_world_embedding_text(self, memory: WorldMemory) -> str:
        parts = [
            f"设定：{memory.name}（{memory.category or ''}）",
            memory.description or "",
            "规则：" + "；".join(map(str, memory.rules or [])),
        ]
        return "\n".join(p for p in parts if p).strip()

    def build_relationship_embedding_text(self, memory: RelationshipMemory) -> str:
        parts = [
            f"关系：{memory.character_a} - {memory.character_b}（{memory.relationship_type or ''}）",
            memory.current_status or "",
        ]
        return "\n".join(p for p in parts if p).strip()

    def _build_text(self, memory_type: str, memory) -> str:
        builders = {
            "chapter": self.build_chapter_embedding_text,
            "character": self.build_character_embedding_text,
            "world": self.build_world_embedding_text,
            "relationship": self.build_relationship_embedding_text,
        }
        builder = builders.get(memory_type)
        return builder(memory) if builder else ""

    async def update_memory_embedding(self, memory_type: str, memory_id: int) -> bool:
        model = _MODEL_MAP.get(memory_type)
        if not model:
            logger.warning(f"未知 memory_type: {memory_type}")
            return False

        memory = self.db.query(model).filter(model.id == memory_id).first()
        if not memory:
            return False

        text = self._build_text(memory_type, memory)
        if not text:
            return False

        try:
            vector = await self.embedding_service.embed_text(text)
        except Exception as e:
            logger.warning(f"记忆向量生成失败 ({memory_type}#{memory_id}): {e}")
            return False

        if not vector:
            return False

        memory.embedding_text = text
        memory.embedding_vector = vector
        memory.embedding_model = self.embedding_service.model_name
        memory.embedding_updated_at = utc_now()
        self.db.commit()
        return True

    async def backfill_project_embeddings(self, project_id: int, limit: int = 100) -> dict:
        result = {"chapter": 0, "character": 0, "world": 0, "relationship": 0}
        for memory_type, model in _MODEL_MAP.items():
            rows = self.db.query(model).filter(
                model.project_id == project_id,
                model.embedding_vector.is_(None),
            ).limit(limit).all()
            for row in rows:
                ok = await self.update_memory_embedding(memory_type, row.id)
                if ok:
                    result[memory_type] += 1
        return result
