"""
MemoryEmbeddingService 单元测试 (P4)
通过 monkeypatch 假 embedding 接口，验证向量写入与回填。
"""

import asyncio

from sqlalchemy.orm import Session

from app.models.chapter import Chapter, ChapterStatus
from app.models.memory import ChapterMemory
from app.models.project import Project
from app.services.memory_embedding_service import MemoryEmbeddingService


def _seed(db_session: Session) -> dict:
    project = Project(name="向量项目", genre="玄幻", status="active")
    db_session.add(project)
    db_session.commit()
    chapter = Chapter(project_id=project.id, chapter_index=30, title="青铜铃初响",
                      status=ChapterStatus.COMPLETED)
    db_session.add(chapter)
    db_session.commit()
    mem = ChapterMemory(
        project_id=project.id, chapter_id=chapter.id, chapter_index=30,
        short_summary="主角获得青铜铃，传闻铃响三次后血脉觉醒。",
        key_events=["获得青铜铃"],
        unresolved_questions=["铃响三次后会怎样"],
    )
    db_session.add(mem)
    db_session.commit()
    return {"project_id": project.id, "memory_id": mem.id}


def test_update_memory_embedding(db_session, monkeypatch):
    info = _seed(db_session)
    service = MemoryEmbeddingService(db_session)

    async def _fake_embed_text(text, model_name=None):
        return [0.1, 0.2, 0.3]

    monkeypatch.setattr(service.embedding_service, "embed_text", _fake_embed_text)

    ok = asyncio.run(service.update_memory_embedding("chapter", info["memory_id"]))
    assert ok is True

    mem = db_session.query(ChapterMemory).filter(
        ChapterMemory.id == info["memory_id"]
    ).first()
    assert mem.embedding_vector == [0.1, 0.2, 0.3]
    assert "青铜铃" in mem.embedding_text


def test_backfill_project_embeddings(db_session, monkeypatch):
    info = _seed(db_session)
    service = MemoryEmbeddingService(db_session)

    async def _fake_embed_text(text, model_name=None):
        return [0.5, 0.5]

    monkeypatch.setattr(service.embedding_service, "embed_text", _fake_embed_text)

    result = asyncio.run(service.backfill_project_embeddings(info["project_id"]))
    assert result["chapter"] == 1


def test_embedding_failure_does_not_raise(db_session, monkeypatch):
    info = _seed(db_session)
    service = MemoryEmbeddingService(db_session)

    async def _fail_embed_text(text, model_name=None):
        return []

    monkeypatch.setattr(service.embedding_service, "embed_text", _fail_embed_text)

    ok = asyncio.run(service.update_memory_embedding("chapter", info["memory_id"]))
    assert ok is False
