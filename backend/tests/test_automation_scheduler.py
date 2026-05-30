"""
P8 自动化调度与生产循环测试
"""

import asyncio

from sqlalchemy.orm import Session

from app.models.automation import AutomationPolicy
from app.models.chapter import Chapter, ChapterStatus
from app.models.memory import ChapterMemory
from app.models.project import Project
from app.services.automation_scheduler_service import AutomationSchedulerService
from app.services.production_loop_service import (
    ProductionLoopService,
    ProductionLoopStatus,
)


def _seed_project_chapters(db_session: Session, completed_count: int) -> int:
    project = Project(name="自动化项目", genre="玄幻", status="active")
    db_session.add(project)
    db_session.commit()
    for i in range(1, completed_count + 1):
        ch = Chapter(project_id=project.id, chapter_index=i, title=f"第{i}章",
                     status=ChapterStatus.COMPLETED, total_score=72.0)
        db_session.add(ch)
        db_session.commit()
        db_session.add(ChapterMemory(
            project_id=project.id, chapter_id=ch.id, chapter_index=i,
            short_summary=f"第{i}章摘要",
        ))
    db_session.commit()
    return project.id


def test_editor_review_triggers_at_n(db_session, monkeypatch):
    project_id = _seed_project_chapters(db_session, 5)
    db_session.add(AutomationPolicy(
        project_id=project_id, enable_editor_review=1,
        editor_review_every_n_chapters=5, enable_research=0, enable_evolution=0,
    ))
    db_session.commit()

    service = AutomationSchedulerService(db_session)

    # 强制 EditorReview 走 fallback（无 LLM）
    from app.services import editor_review_service as ers

    async def _fail_llm(self, *a, **k):
        return None
    monkeypatch.setattr(ers.EditorReviewService, "_llm_review", _fail_llm)

    result = asyncio.run(service.maybe_run_editor_review(project_id))
    assert result["triggered"] is True
    assert result["end_chapter"] == 5
    assert "next_adjustments" in result["review"]


def test_editor_review_no_double_trigger(db_session, monkeypatch):
    project_id = _seed_project_chapters(db_session, 5)
    db_session.add(AutomationPolicy(
        project_id=project_id, enable_editor_review=1,
        editor_review_every_n_chapters=5, enable_research=0, enable_evolution=0,
    ))
    db_session.commit()

    service = AutomationSchedulerService(db_session)
    from app.services import editor_review_service as ers

    async def _fail_llm(self, *a, **k):
        return None
    monkeypatch.setattr(ers.EditorReviewService, "_llm_review", _fail_llm)

    asyncio.run(service.maybe_run_editor_review(project_id))
    again = asyncio.run(service.maybe_run_editor_review(project_id))
    assert again["triggered"] is False


def test_evolution_trigger(db_session):
    project_id = _seed_project_chapters(db_session, 5)
    db_session.add(AutomationPolicy(
        project_id=project_id, enable_editor_review=0,
        enable_research=0, enable_evolution=1,
        evolution_check_every_n_chapters=5,
    ))
    db_session.commit()

    service = AutomationSchedulerService(db_session)
    result = asyncio.run(service.maybe_run_evolution(project_id))
    assert result["triggered"] is True
    assert result["end_chapter"] == 5


def test_scan_without_policy(db_session):
    project = Project(name="无策略", genre="玄幻", status="active")
    db_session.add(project)
    db_session.commit()
    service = AutomationSchedulerService(db_session)
    result = asyncio.run(service.scan_project_automations(project.id))
    assert "skipped" in result


def test_production_loop_status_lifecycle():
    loop = ProductionLoopService()
    assert loop.get_status()["status"] == ProductionLoopStatus.STOPPED.value
    asyncio.run(loop.pause())  # 停止态 pause 不应崩溃
    status = loop.get_status()
    assert "interval_seconds" in status
    assert "last_scan_at" in status
