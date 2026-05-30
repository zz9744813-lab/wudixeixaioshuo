"""
Reader training prompt injection tests.

These guard the P3 loop: processed human reader rules must reach the real
Planner/Draft/Critic/Rewrite prompts and be visible in GenerationStep metadata.
"""

import asyncio

from sqlalchemy.orm import Session

import app.services.pipeline_service as pipeline_module
from app.models.chapter import Chapter
from app.models.project import Project
from app.models.prompt_template import PromptTemplate
from app.models.task import GenerationTask, GenerationStep, TaskStatus
from app.services.pipeline_service import PipelineService


class _FakeLLM:
    async def generate(self, prompt, role="default", **kwargs):
        if role == "critic":
            return {
                "content": (
                    '{"overall_score": 82, "dimension_scores": {"reader_addiction": 80}, '
                    '"anchored_comments": {}, "line_comments": [], '
                    '"must_fix_items": [], "nice_to_have_items": [], "rewrite_plan": []}'
                ),
                "total_tokens": 5,
                "cost": 0.001,
                "model": "fake",
                "provider": "fake",
            }
        return {
            "content": "正文内容" * 200,
            "total_tokens": 10,
            "cost": 0.002,
            "model": "fake",
            "provider": "fake",
        }


def _seed(db_session: Session) -> dict:
    db_session.query(PromptTemplate).filter(
        PromptTemplate.role.in_(["draft", "critic", "planner", "rewrite"])
    ).update({"is_active": 0}, synchronize_session=False)
    db_session.commit()

    project = Project(name="reader rules injection", genre="fantasy", status="active")
    db_session.add(project)
    db_session.commit()
    chapter = Chapter(
        project_id=project.id,
        chapter_index=3,
        title="第三章",
        status="planned",
    )
    db_session.add(chapter)
    db_session.commit()
    task = GenerationTask(
        project_id=project.id,
        chapter_id=chapter.id,
        task_type="draft",
        status=TaskStatus.RUNNING,
    )
    db_session.add(task)
    db_session.commit()
    return {
        "task_id": task.id,
        "chapter_id": chapter.id,
        "project_id": project.id,
        "chapter_title": "第三章",
        "chapter_index": 3,
    }


def _rules(role: str) -> dict:
    return {
        role: [{
            "role": role,
            "rule": f"reader-rule-{role}-unique",
            "priority": 9,
            "evidence": ["reader evidence"],
            "batch_id": 12,
        }]
    }


def _assert_step_has_rule(db_session: Session, agent: str, role: str):
    step = db_session.query(GenerationStep).filter(
        GenerationStep.agent_name == agent
    ).order_by(GenerationStep.id.desc()).first()
    assert step is not None
    assert f"reader-rule-{role}-unique" in (step.input_prompt or "")
    assert (step.context_metadata or {})["reader_rules"][role][0]["rule"] == (
        f"reader-rule-{role}-unique"
    )


def test_planner_prompt_contains_reader_rules(db_session, monkeypatch):
    monkeypatch.setattr(pipeline_module, "llm_manager", _FakeLLM())
    monkeypatch.setattr(pipeline_module, "SessionLocal", lambda: db_session)
    task_info = _seed(db_session)

    asyncio.run(
        PipelineService()._run_planner(
            task_info, {}, "记忆", None, None, None, _rules("planner")
        )
    )

    _assert_step_has_rule(db_session, "Planner", "planner")


def test_draft_prompt_contains_reader_rules(db_session, monkeypatch):
    monkeypatch.setattr(pipeline_module, "llm_manager", _FakeLLM())
    monkeypatch.setattr(pipeline_module, "SessionLocal", lambda: db_session)
    task_info = _seed(db_session)

    asyncio.run(
        PipelineService()._run_draft(
            task_info, {}, {"content": "计划"}, "记忆", None, None, None, _rules("draft")
        )
    )

    _assert_step_has_rule(db_session, "Draft", "draft")


def test_critic_prompt_contains_reader_rules(db_session, monkeypatch):
    monkeypatch.setattr(pipeline_module, "llm_manager", _FakeLLM())
    monkeypatch.setattr(pipeline_module, "SessionLocal", lambda: db_session)
    task_info = _seed(db_session)

    asyncio.run(
        PipelineService()._run_critic(
            task_info, "一段正文", {}, None, None, _rules("critic")
        )
    )

    _assert_step_has_rule(db_session, "Critic", "critic")


def test_rewrite_prompt_contains_reader_rules(db_session, monkeypatch):
    monkeypatch.setattr(pipeline_module, "llm_manager", _FakeLLM())
    monkeypatch.setattr(pipeline_module, "SessionLocal", lambda: db_session)
    task_info = _seed(db_session)

    asyncio.run(
        PipelineService()._run_rewrite_if_needed(
            task_info,
            "旧正文",
            {"must_fix_items": ["修节奏"], "rewrite_plan": ["第一轮修节奏"]},
            {},
            70,
            "记忆",
            None,
            None,
            ["追读欲不足"],
            _rules("rewrite"),
        )
    )

    _assert_step_has_rule(db_session, "Rewrite", "rewrite")
