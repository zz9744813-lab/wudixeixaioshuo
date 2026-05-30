import pytest
from sqlalchemy.orm import Session

from app.models.agent_run import AgentRunStatus
from app.models.chapter import Chapter
from app.models.project import Project
from app.models.task import GenerationTask
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
async def test_orchestrator_pauses_when_approval_required(db_session: Session):
    service = OrchestratorService(db_session)
    run = await service.start_run(user_request="先规划一个小说项目", mode="require_approval")

    finished = await service.execute_run(run.id)

    assert finished.status == AgentRunStatus.PAUSED
    assert "等待用户确认计划" in finished.final_report
