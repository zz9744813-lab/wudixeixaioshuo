"""
P1 知识注入集成测试
验证 Draft / Critic Prompt 注入了联网研究知识，且落到 GenerationStep.input_prompt。
"""

import asyncio

import pytest
from sqlalchemy.orm import Session

import app.services.pipeline_service as pipeline_module
from app.models.project import Project
from app.models.chapter import Chapter
from app.models.task import GenerationTask, GenerationStep, TaskStatus
from app.models.prompt_template import PromptTemplate
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


def _seed(db_session: Session):
    # 清理可能由其它测试遗留的活跃模板，确保走 fallback 注入路径
    db_session.query(PromptTemplate).filter(
        PromptTemplate.role.in_(["draft", "critic", "planner"])
    ).update({"is_active": 0}, synchronize_session=False)
    db_session.commit()

    project = Project(name="注入项目", genre="玄幻", status="active")
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


_KNOWLEDGE = {
    "patterns": [{
        "pattern_name": "开局打脸", "pattern_type": "opening",
        "description": "开局反转打脸建立爽点。",
        "applicable_scene": "第一章", "anti_patterns": "勿拖沓",
    }],
    "reader_insights": [{
        "insight_type": "dislike", "title": "忌讳圣母",
        "description": "读者反感无原则原谅。", "evidence": "差评高频",
    }],
}


def test_draft_prompt_contains_knowledge(db_session, monkeypatch):
    monkeypatch.setattr(pipeline_module, "llm_manager", _FakeLLM())
    monkeypatch.setattr(pipeline_module, "SessionLocal", lambda: db_session)

    task_info = _seed(db_session)
    service = PipelineService()

    asyncio.run(
        service._run_draft(task_info, {}, {"content": "计划"}, "记忆", None, _KNOWLEDGE)
    )

    step = db_session.query(GenerationStep).filter(
        GenerationStep.agent_name == "Draft"
    ).first()
    assert step is not None
    assert "联网研究知识" in (step.input_prompt or "")


def test_critic_prompt_contains_knowledge(db_session, monkeypatch):
    monkeypatch.setattr(pipeline_module, "llm_manager", _FakeLLM())
    monkeypatch.setattr(pipeline_module, "SessionLocal", lambda: db_session)

    task_info = _seed(db_session)
    service = PipelineService()

    asyncio.run(
        service._run_critic(task_info, "一段正文", {}, _KNOWLEDGE)
    )

    step = db_session.query(GenerationStep).filter(
        GenerationStep.agent_name == "Critic"
    ).first()
    assert step is not None
    assert "联网研究审稿依据" in (step.input_prompt or "")
