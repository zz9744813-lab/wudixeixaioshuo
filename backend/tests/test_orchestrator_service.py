import pytest
from sqlalchemy.orm import Session

from app.models.agent_run import AgentPlan, AgentRunStatus
from app.models.chapter import Chapter
from app.models.project import Project
from app.models.task import GenerationTask
from app.services.agent_planner_service import AgentPlanValidationError, AgentPlannerService
from app.services.orchestrator_service import OrchestratorService


@pytest.mark.asyncio
async def test_orchestrator_executes_p0_main_flow(db_session: Session):
    service = OrchestratorService(db_session)
    run = await service.start_run(
        user_request="创建一部东方修仙系统流小说，面向起点读者，目标 200万字，日更1万。",
        max_steps=30,
    )

    finished = await service.execute_run(run.id)

    assert finished.status == AgentRunStatus.SUCCEEDED
    assert finished.final_report is not None

    projects = db_session.query(Project).all()
    assert len(projects) == 1
    assert finished.project_id == projects[0].id
    assert projects[0].genre == "东方修仙"
    assert projects[0].bible is not None

    chapters = db_session.query(Chapter).filter(Chapter.project_id == projects[0].id).all()
    assert len(chapters) == 3

    queued_tasks = db_session.query(GenerationTask).filter(GenerationTask.project_id == projects[0].id).all()
    assert len(queued_tasks) == 3

    status = service.get_run_status(run.id)
    assert status["plans"]
    assert len(status["steps"]) == 7
    assert all(step["status"] == "succeeded" for step in status["steps"])



@pytest.mark.asyncio
async def test_agent_planner_falls_back_to_valid_rule_plan(db_session: Session):
    planner = AgentPlannerService(db_session)

    plan = await planner.create_plan(
        user_request="创建一部东方修仙系统流小说，先规划五章。",
        max_steps=30,
    )

    assert plan["planner_source"] == "fallback"
    assert plan["planner_model"] == "rule-based-p0"
    assert [step["tool_name"] for step in plan["steps"]][-1] == "build_report"
    outline_step = next(step for step in plan["steps"] if step["tool_name"] == "plan_outline")
    assert outline_step["args"]["chapter_count"] == 5


def test_agent_planner_rejects_unknown_tool(db_session: Session):
    planner = AgentPlannerService(db_session)

    with pytest.raises(AgentPlanValidationError):
        planner.validate_plan({
            "title": "非法计划",
            "summary": "包含不存在工具",
            "steps": [
                {"step_key": "bad", "title": "坏步骤", "tool_name": "fake_tool", "args": {}, "depends_on": []},
            ],
        })


@pytest.mark.asyncio
async def test_orchestrator_pauses_when_max_steps_exceeded(db_session: Session):
    service = OrchestratorService(db_session)
    run = await service.start_run(user_request="创建一部小说", max_steps=1)

    finished = await service.execute_run(run.id)

    assert finished.status == AgentRunStatus.PAUSED
    assert "预算或最大步骤数超限" in finished.final_report


@pytest.mark.asyncio
async def test_orchestrator_resume_and_report_helpers(db_session: Session):
    service = OrchestratorService(db_session)
    run = await service.start_run(user_request="先规划一个小说项目", mode="require_approval")

    paused = await service.execute_run(run.id)
    assert paused.status == AgentRunStatus.PAUSED

    resumed = await service.resume_run(run.id)
    assert resumed.status == AgentRunStatus.SUCCEEDED

    steps = service.get_run_steps(run.id)
    events = service.get_run_events(run.id)
    report = service.get_run_report(run.id)

    assert len(steps) == 7
    assert any(event["event"] == "agent_step_succeeded" for event in events)
    assert report["report"]["title"] == "自主 Agent 立项报告"

    plan = db_session.query(AgentPlan).filter(AgentPlan.run_id == run.id).first()
    assert plan.planner_model == "rule-based-p0"
