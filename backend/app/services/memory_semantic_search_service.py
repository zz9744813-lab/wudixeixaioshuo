"""
MemorySemanticSearchService - 语义记忆召回 (P4)
基于 JSON 存储的 embedding 向量做 Python cosine 相似度检索。
"""

import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.memory import (
    CharacterMemory,
    ChapterMemory,
    RelationshipMemory,
    WorldMemory,
)
from app.services.embedding_service import EmbeddingService
from app.utils.vector_utils import cosine_similarity

logger = logging.getLogger(__name__)


class MemorySemanticSearchService:
    """语义记忆检索"""

    def __init__(self, db: Session):
        self.db = db
        self.embedding_service = EmbeddingService(db)

    async def search(
        self,
        project_id: int,
        query_text: str,
        memory_types: Optional[List[str]] = None,
        top_k: int = 10,
        min_score: float = 0.25,
    ) -> List[dict]:
        if not query_text:
            return []

        query_vec = await self.embedding_service.embed_text(query_text)
        if not query_vec:
            return []

        memory_types = memory_types or ["chapter", "character", "world", "relationship"]
        candidates = []
        for mtype in memory_types:
            candidates.extend(self._collect(project_id, mtype))

        scored = []
        for item in candidates:
            vec = item.get("embedding_vector")
            if not vec:
                continue
            score = cosine_similarity(query_vec, vec)
            if score >= min_score:
                item["score"] = round(score, 4)
                item.pop("embedding_vector", None)
                scored.append(item)

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def _collect(self, project_id: int, mtype: str) -> List[dict]:
        if mtype == "chapter":
            rows = self.db.query(ChapterMemory).filter(
                ChapterMemory.project_id == project_id,
                ChapterMemory.embedding_vector.isnot(None),
            ).all()
            return [{
                "memory_type": "chapter",
                "id": r.id,
                "title": f"第{r.chapter_index}章",
                "text": r.embedding_text or r.short_summary or "",
                "chapter_index": r.chapter_index,
                "importance_score": None,
                "embedding_vector": r.embedding_vector,
            } for r in rows]

        if mtype == "character":
            rows = self.db.query(CharacterMemory).filter(
                CharacterMemory.project_id == project_id,
                CharacterMemory.embedding_vector.isnot(None),
            ).all()
            return [{
                "memory_type": "character",
                "id": r.id,
                "title": r.name,
                "text": r.embedding_text or r.summary or "",
                "chapter_index": None,
                "importance_score": r.importance_score,
                "embedding_vector": r.embedding_vector,
            } for r in rows]

        if mtype == "world":
            rows = self.db.query(WorldMemory).filter(
                WorldMemory.project_id == project_id,
                WorldMemory.embedding_vector.isnot(None),
            ).all()
            return [{
                "memory_type": "world",
                "id": r.id,
                "title": r.name,
                "text": r.embedding_text or r.description or "",
                "chapter_index": None,
                "importance_score": r.importance_score,
                "embedding_vector": r.embedding_vector,
            } for r in rows]

        if mtype == "relationship":
            rows = self.db.query(RelationshipMemory).filter(
                RelationshipMemory.project_id == project_id,
                RelationshipMemory.embedding_vector.isnot(None),
            ).all()
            return [{
                "memory_type": "relationship",
                "id": r.id,
                "title": f"{r.character_a}-{r.character_b}",
                "text": r.embedding_text or r.current_status or "",
                "chapter_index": None,
                "importance_score": None,
                "embedding_vector": r.embedding_vector,
            } for r in rows]

        return []
