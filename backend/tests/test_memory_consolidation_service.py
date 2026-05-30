"""
MemoryConsolidationService 单元测试 (P5)
"""

import asyncio

from sqlalchemy.orm import Session

from app.models.chapter import Chapter, ChapterStatus
from app.models.memory import ChapterMemory, ConsolidatedMemory
from app.models.project import Project
from app.services.memory_consolidation_service import MemoryConsolidationService


def _seed_chapters(db_session: Session, project_id: int, start: int, end: int):
    for i in range(start, end + 1):
        ch = Chapter(project_id=project_id, chapter_index=i, title=f"第{i}章",
                     status=ChapterStatus.COMPLETED)
        db_session.add(ch)
        db_session.commit()
        db_session.add(ChapterMemory(
            project_id=project_id, chapter_id=ch.id, chapter_index=i,
            short_summary=f"第{i}章发生关键事件{i}。",
            key_events=[f"事件{i}"],
            unresolved_questions=[f"悬念{i}"] if i % 3 == 0 else [],
        ))
        db_session.commit()


def _make_project(db_session: Session) -> int:
    project = Project(name="固化项目", genre="玄幻", status="active")
    db_session.add(project)
    db_session.commit()
    return project.id


def test_consolidate_if_needed_triggers_at_10(db_session, monkeypatch):
    project_id = _make_project(db_session)
    _seed_chapters(db_session, project_id, 1, 10)
    service = MemoryConsolidationService(db_session)

    # 强制走 fallback（无 LLM）
    async def _fail_llm(*args, **kwargs):
        return None
    monkeypatch.setattr(service, "_llm_consolidate", _fail_llm)

    result = asyncio.run(service.consolidate_if_needed(project_id, every_n_chapters=10))
    assert result
    assert result["title"]

    rows = db_session.query(ConsolidatedMemory).filter(
        ConsolidatedMemory.project_id == project_id
    ).all()
    assert len(rows) == 1
    assert rows[0].scope_start_chapter == 1
    assert rows[0].scope_end_chapter == 10


def test_consolidate_if_needed_no_trigger_at_9(db_session, monkeypatch):
    project_id = _make_project(db_session)
    _seed_chapters(db_session, project_id, 1, 9)
    service = MemoryConsolidationService(db_session)

    result = asyncio.run(service.consolidate_if_needed(project_id, every_n_chapters=10))
    assert result == {}


def test_consolidate_range_no_duplicate(db_session, monkeypatch):
    project_id = _make_project(db_session)
    _seed_chapters(db_session, project_id, 1, 10)
    service = MemoryConsolidationService(db_session)

    async def _fail_llm(*args, **kwargs):
        return None
    monkeypatch.setattr(service, "_llm_consolidate", _fail_llm)

    asyncio.run(service.consolidate_if_needed(project_id, every_n_chapters=10))
    # 第二次不应重复插入
    again = asyncio.run(service.consolidate_if_needed(project_id, every_n_chapters=10))
    assert again == {}
    rows = db_session.query(ConsolidatedMemory).filter(
        ConsolidatedMemory.project_id == project_id
    ).all()
    assert len(rows) == 1
