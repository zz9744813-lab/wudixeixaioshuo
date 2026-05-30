"""
P7 并行 Draft 候选测试
"""

import asyncio

from sqlalchemy.orm import Session

import app.services.pipeline_service as pipeline_module
from app.models.chapter import Chapter
from app.models.prompt_template import PromptTemplate
from app.models.project import Project
from app.models.task import GenerationTask, GenerationStep, TaskStatus
from app.services.pipeline_service import PipelineService


class _FakeLLM:
    async def generate(self, prompt, role="default", **kwargs):
        if role == "critic":
            return {"content": '{"overall_score": 80, "dimension_scores": {"reader_addiction": 78}}',
                    "total_tokens": 5, "cost": 0.001}
        return {"content": "正文内容" * 200, "total_tokens": 10, "cost": 0.002,
                "model": "fake", "provider": "fake"}


def _seed(db_session: Session) -> dict:
    db_session.query(PromptTemplate).filter(
        PromptTemplate.role.in_(["draft", "critic", "planner"])
    ).update({"is_active": 0}, synchronize_session=False)
    db_session.commit()
    project = Project(name="并行Draft项目", genre="玄幻", status="active")
    db_session.add(project)
    db_session.commit()
    chapter = Chapter(project_id=project.id, chapter_index=1, title="第一章", status="planned")
    db_session.add(chapter)
    db_session.commit()
    task = GenerationTask(project_id=project.id, chapter_id=chapter.id,
                          task_type="draft", status=TaskStatus.RUNNING)
    db_session.add(task)
    db_session.commit()
    return {"task_id": task.id, "chapter_id": chapter.id, "project_id": project.id,
            "chapter_title": "第一章", "chapter_index": 1}


def test_parallel_draft_returns_candidates(db_session, monkeypatch):
    monkeypatch.setattr(pipeline_module, "llm_manager", _FakeLLM())
    monkeypatch.setattr(pipeline_module, "SessionLocal", lambda: db_session)
    task_info = _seed(db_session)
    service = PipelineService()

    result = asyncio.run(service._run_parallel_draft_candidates(
        task_info, {}, {"content": "计划"}, "记忆",
        candidate_count=3, max_concurrency=3,
    ))

    assert result["success"] is True
    assert result["agent"] == "ParallelDraft"
    assert len(result["candidates"]) == 3
    assert result["selected_candidate_id"]
    assert result["selection_reason"]


def test_parallel_draft_saves_selection_step(db_session, monkeypatch):
    monkeypatch.setattr(pipeline_module, "llm_manager", _FakeLLM())
    monkeypatch.setattr(pipeline_module, "SessionLocal", lambda: db_session)
    task_info = _seed(db_session)
    service = PipelineService()

    asyncio.run(service._run_parallel_draft_candidates(
        task_info, {}, {"content": "计划"}, "记忆",
        candidate_count=2, max_concurrency=2,
    ))

    step = db_session.query(GenerationStep).filter(
        GenerationStep.agent_name == "ParallelDraft"
    ).first()
    assert step is not None
    assert "选中" in (step.parsed_output or step.raw_output or "")
