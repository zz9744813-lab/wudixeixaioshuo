"""
P4 语义记忆召回测试
第30章埋伏笔"铃响三次后血脉觉醒"，第120章查询应召回第30章。
"""

import asyncio

from sqlalchemy.orm import Session

from app.models.chapter import Chapter, ChapterStatus
from app.models.memory import ChapterMemory
from app.models.project import Project
from app.services.memory_semantic_search_service import MemorySemanticSearchService


def _seed(db_session: Session) -> int:
    project = Project(name="召回项目", genre="玄幻", status="active")
    db_session.add(project)
    db_session.commit()

    # 第30章：青铜铃方向向量
    c30 = Chapter(project_id=project.id, chapter_index=30, title="青铜铃初响",
                  status=ChapterStatus.COMPLETED)
    # 无关章节：村庄日常
    c50 = Chapter(project_id=project.id, chapter_index=50, title="村庄日常",
                  status=ChapterStatus.COMPLETED)
    db_session.add_all([c30, c50])
    db_session.commit()

    db_session.add(ChapterMemory(
        project_id=project.id, chapter_id=c30.id, chapter_index=30,
        short_summary="主角获得青铜铃，铃响三次后血脉觉醒。",
        embedding_text="青铜铃 铃响三次 血脉觉醒",
        embedding_vector=[1.0, 0.0, 0.0],
        embedding_model="fake",
    ))
    db_session.add(ChapterMemory(
        project_id=project.id, chapter_id=c50.id, chapter_index=50,
        short_summary="主角在村庄歇脚，与村民闲聊。",
        embedding_text="村庄 日常 闲聊",
        embedding_vector=[0.0, 1.0, 0.0],
    ))
    db_session.commit()
    return project.id


def test_semantic_recall_hits_chapter_30(db_session, monkeypatch):
    project_id = _seed(db_session)
    service = MemorySemanticSearchService(db_session)

    async def _fake_embed_text(text, model_name=None):
        # 查询第三次铃声，方向与第30章一致
        return [1.0, 0.0, 0.0]

    monkeypatch.setattr(service.embedding_service, "embed_text", _fake_embed_text)

    results = asyncio.run(service.search(
        project_id=project_id,
        query_text="第三次铃声 血脉觉醒",
        memory_types=["chapter"],
        top_k=5,
    ))

    assert len(results) >= 1
    top = results[0]
    assert top["chapter_index"] == 30
    assert "青铜铃" in top["text"] or "血脉觉醒" in top["text"]


def test_semantic_recall_filters_low_score(db_session, monkeypatch):
    project_id = _seed(db_session)
    service = MemorySemanticSearchService(db_session)

    async def _fake_embed_text(text, model_name=None):
        return [1.0, 0.0, 0.0]

    monkeypatch.setattr(service.embedding_service, "embed_text", _fake_embed_text)

    results = asyncio.run(service.search(
        project_id=project_id,
        query_text="任意",
        memory_types=["chapter"],
        top_k=5,
        min_score=0.5,
    ))
    # 村庄章节方向正交，相似度 0，应被过滤
    idxs = [r["chapter_index"] for r in results]
    assert 50 not in idxs


def test_empty_query_returns_empty(db_session):
    project_id = _seed(db_session)
    service = MemorySemanticSearchService(db_session)
    results = asyncio.run(service.search(project_id=project_id, query_text=""))
    assert results == []
