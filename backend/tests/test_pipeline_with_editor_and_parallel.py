"""
P7 端到端：总编指令 + 并行 Draft/Critic 同时启用时 Pipeline 不崩溃。
通过开关打开并行路径，验证单步方法可独立工作。
"""

import asyncio

from sqlalchemy.orm import Session

import app.services.pipeline_service as pipeline_module
from app.config import settings
from app.models.chapter import Chapter
from app.models.prompt_template import PromptTemplate
from app.models.project import Project
from app.models.task import GenerationTask, TaskStatus
from app.services.pipeline_service import PipelineService


class _FakeLLM:
    async def generate(self, prompt, role="default", **kwargs):
        if role == "critic":
            return {"content": '{"overall_score": 83, "dimension_scores": {"reader_addiction": 81}, '
                               '"must_fix_items": [], "rewrite_plan": []}',
                    "total_tokens": 5, "cost": 0.001}
        return {"content": "正文内容" * 200, "total_tokens": 10, "cost": 0.002,
                "model": "fake", "provider": "fake"}


def _seed(db_session: Session) -> dict:
    db_session.query(PromptTemplate).filter(
        PromptTemplate.role.in_(["draft", "critic", "planner"])
    ).update({"is_active": 0}, synchronize_session=False)
    db_session.commit()
    project = Project(name="端到端项目", genre="玄幻", status="active")
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


_DIRECTIVE = {
    "global_position": {"volume": "第一卷", "arc": "入局", "stage": "升级", "chapter_role": "失败"},
    "tension_target": {"start_level": 4, "peak_level": 7, "ending_level": 8, "emotion_curve": "压迫"},
    "plot_goals": ["推进主线"],
    "foreshadow_goals": ["神秘玉佩"],
}


def test_parallel_draft_with_directive(db_session, monkeypatch):
    monkeypatch.setattr(pipeline_module, "llm_manager", _FakeLLM())
    monkeypatch.setattr(pipeline_module, "SessionLocal", lambda: db_session)
    task_info = _seed(db_session)
    service = PipelineService()

    result = asyncio.run(service._run_parallel_draft_candidates(
        task_info, {}, {"content": "计划"}, "记忆",
        editor_directive=_DIRECTIVE, candidate_count=2, max_concurrency=2,
    ))
    assert result["success"] is True
    assert result["selected_content"]


def test_parallel_flags_default_off():
    # 默认配置下并行开关应关闭，保证成本可控
    assert settings.ENABLE_PARALLEL_DRAFT is False
    assert settings.ENABLE_PARALLEL_CRITIC is False


def test_is_parallel_enabled_reflects_settings(db_session, monkeypatch):
    service = PipelineService()
    monkeypatch.setattr(settings, "ENABLE_PARALLEL_DRAFT", True)
    monkeypatch.setattr(settings, "ENABLE_PARALLEL_CRITIC", True)
    assert service._is_parallel_draft_enabled(1) is True
    assert service._is_parallel_critic_enabled(1) is True
