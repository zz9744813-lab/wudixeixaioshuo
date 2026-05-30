"""
BookStateService 单元测试 (P2)
"""

import asyncio

from sqlalchemy.orm import Session

from app.models.chapter import Chapter, ChapterStatus
from app.models.foreshadow import Foreshadow
from app.models.memory import ChapterMemory
from app.models.project import Project
from app.services.book_state_service import BookStateService


def _seed(db_session: Session) -> dict:
    project = Project(name="书态项目", genre="玄幻", status="active")
    db_session.add(project)
    db_session.commit()

    chapter = Chapter(
        project_id=project.id, chapter_index=1, title="第一章",
        status=ChapterStatus.COMPLETED,
    )
    db_session.add(chapter)
    db_session.commit()

    db_session.add(ChapterMemory(
        project_id=project.id, chapter_id=chapter.id, chapter_index=1,
        short_summary="主角登场并遭遇危机。",
        key_events=["登场", "遇袭"],
        unresolved_questions=["神秘人是谁"],
    ))
    db_session.add(Foreshadow(
        project_id=project.id, title="神秘玉佩", status="ready_to_payoff",
    ))
    db_session.add(Foreshadow(
        project_id=project.id, title="师门往事", status="planted",
    ))
    db_session.commit()
    return {"project_id": project.id, "chapter_id": chapter.id}


def test_update_from_completed_chapter(db_session: Session):
    info = _seed(db_session)
    service = BookStateService(db_session)

    state = asyncio.run(
        service.update_from_completed_chapter(info["project_id"], info["chapter_id"])
    )

    assert len(state.tension_curve) == 1
    assert state.tension_curve[0]["chapter_index"] == 1
    assert state.tension_curve[0]["events"] == 2
    assert "神秘人是谁" in state.unresolved_conflicts
    assert state.last_analyzed_chapter_index == 1
    assert state.summary == "主角登场并遭遇危机。"
    titles = [f["title"] for f in state.active_foreshadows]
    assert "神秘玉佩" in titles and "师门往事" in titles
    assert [c["title"] for c in state.next_payoff_candidates] == ["神秘玉佩"]


def test_get_or_create_state_idempotent(db_session: Session):
    info = _seed(db_session)
    service = BookStateService(db_session)
    s1 = asyncio.run(service.get_or_create_state(info["project_id"]))
    s2 = asyncio.run(service.get_or_create_state(info["project_id"]))
    assert s1.id == s2.id


def test_rebuild_state(db_session: Session):
    info = _seed(db_session)
    service = BookStateService(db_session)
    state = asyncio.run(service.rebuild_state(info["project_id"]))
    assert len(state.tension_curve) == 1
    assert state.last_analyzed_chapter_index == 1
