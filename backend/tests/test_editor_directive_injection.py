"""
P2 总编指令注入集成测试
验证 Planner / Draft / Critic Prompt 注入了总编全局指令，且落到 GenerationStep.input_prompt。
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
    async def generate(self, *args, **kwargs):
        return {
            "content": "正文内容" * 200,
            "total_tokens": 10,
            "cost": 0.0,
            "model": "fake",
            "provider": "fake",
        }


_DIRECTIVE = {
    "global_position": {"volume": "第一卷", "arc": "入局", "stage": "升级", "chapter_role": "制造首次失败"},
    "tension_target": {"start_level": 4, "peak_level": 7, "ending_level": 8, "emotion_curve": "压迫→反抗"},
    "plot_goals": ["推进主线"],
    "payoff_goals": [],
    "foreshadow_goals": ["神秘玉佩"],
    "character_arc_goals": {},
    "commercial_goals": {"main_hook": "反转", "爽点类型": "打脸", "avoid": []},
    "risk_warnings": [],
}


def _seed(db_session: Session) -> dict:
    db_session.query(PromptTemplate).filter(
        PromptTemplate.role.in_(["draft", "critic", "planner"])
    ).update({"is_active": 0}, synchronize_session=False)
    db_session.commit()

    project = Project(name="指令注入项目", genre="玄幻", status="active")
    db_session.add(project)
    db_session.commit()
    chapter = Chapter(project_id=project.id, chapter_index=1, title="第一章", status="planned")
    db_session.add(chapter)
    db_session.commit()
    task = GenerationTask(
        project_id=project.id, chapter_id=chapter.id,
        task_type="draft", status=TaskStatus.RUNNING,
    )
    db_session.add(task)
    db_session.commit()
    return {
        "task_id": task.id,
        "chapter_id": chapter.id,
        "project_id": project.id,
        "chapter_title": "第一章",
        "chapter_index": 1,
    }


def test_planner_prompt_contains_directive(db_session, monkeypatch):
    monkeypatch.setattr(pipeline_module, "llm_manager", _FakeLLM())
    monkeypatch.setattr(pipeline_module, "SessionLocal", lambda: db_session)

    task_info = _seed(db_session)
    service = PipelineService()

    asyncio.run(service._run_planner(task_info, {}, "记忆", None, None, _DIRECTIVE))

    step = db_session.query(GenerationStep).filter(
        GenerationStep.agent_name == "Planner"
    ).first()
    assert step is not None
    assert "总编全局指令" in (step.input_prompt or "")


def test_draft_prompt_contains_directive(db_session, monkeypatch):
    monkeypatch.setattr(pipeline_module, "llm_manager", _FakeLLM())
    monkeypatch.setattr(pipeline_module, "SessionLocal", lambda: db_session)

    task_info = _seed(db_session)
    service = PipelineService()

    asyncio.run(
        service._run_draft(task_info, {}, {"content": "计划"}, "记忆", None, None, _DIRECTIVE)
    )

    step = db_session.query(GenerationStep).filter(
        GenerationStep.agent_name == "Draft"
    ).first()
    assert step is not None
    assert "本章全局写作目标" in (step.input_prompt or "")


def test_critic_prompt_contains_directive(db_session, monkeypatch):
    monkeypatch.setattr(pipeline_module, "llm_manager", _FakeLLM())
    monkeypatch.setattr(pipeline_module, "SessionLocal", lambda: db_session)

    task_info = _seed(db_session)
    service = PipelineService()

    asyncio.run(service._run_critic(task_info, "一段正文", {}, None, _DIRECTIVE))

    step = db_session.query(GenerationStep).filter(
        GenerationStep.agent_name == "Critic"
    ).first()
    assert step is not None
    assert "总编指令达成度检查" in (step.input_prompt or "")
