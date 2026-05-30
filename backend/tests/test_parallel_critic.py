"""
P7 并行 Critic 测试
"""

import asyncio

from sqlalchemy.orm import Session

import app.services.pipeline_service as pipeline_module
from app.models.chapter import Chapter
from app.models.prompt_template import PromptTemplate
from app.models.project import Project
from app.models.task import GenerationTask, TaskStatus
from app.services.pipeline_service import PipelineService


class _FakeLLM:
    async def generate(self, prompt, role="default", **kwargs):
        return {"content": '{"overall_score": 82, "dimension_scores": {"reader_addiction": 80}, '
                           '"must_fix_items": ["修复A"], "rewrite_plan": ["第1轮"]}',
                "total_tokens": 5, "cost": 0.001}


def _seed(db_session: Session) -> dict:
    db_session.query(PromptTemplate).filter(
        PromptTemplate.role.in_(["draft", "critic", "planner"])
    ).update({"is_active": 0}, synchronize_session=False)
    db_session.commit()
    project = Project(name="并行Critic项目", genre="玄幻", status="active")
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


def test_parallel_critics_aggregate(db_session, monkeypatch):
    monkeypatch.setattr(pipeline_module, "llm_manager", _FakeLLM())
    monkeypatch.setattr(pipeline_module, "SessionLocal", lambda: db_session)
    task_info = _seed(db_session)
    service = PipelineService()

    result = asyncio.run(service._run_parallel_critics(
        task_info, "一段正文", {}, None, None
    ))

    assert result["success"] is True
    assert result["agent"] == "ParallelCritic"
    assert len(result["critic_reports"]) == 4
    critics = {r["critic"] for r in result["critic_reports"]}
    assert {"commercial", "continuity", "character", "style"} == critics
    assert result["score"] > 0
    assert "修复A" in result["merged_must_fix_items"]
    # 必修项去重
    assert result["merged_must_fix_items"].count("修复A") == 1
