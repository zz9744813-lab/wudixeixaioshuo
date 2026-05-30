import pytest
from sqlalchemy.orm import Session

from app.models.agent_run import AgentRun, SubAgentTaskStatus
from app.services.subagent_service import SubAgentService


@pytest.mark.asyncio
async def test_create_and_run_subagent_task_with_local_fallback(db_session: Session):
    run = AgentRun(user_request="测试自主运行", status="running")
    db_session.add(run)
    db_session.commit()

    service = SubAgentService(db_session)
    tasks = await service.create_tasks_from_plan(
        run_id=run.id,
        parent_step_id=None,
        task_specs=[{"task_type": "critic", "title": "风险检查", "role": "critic", "input_prompt": "检查风险"}],
    )

    assert len(tasks) == 1
    assert tasks[0].status == SubAgentTaskStatus.PENDING

    executed = await service.run_task(tasks[0].id, use_llm=False)

    assert executed.status == SubAgentTaskStatus.SUCCEEDED
    assert executed.provider_name == "local-rule-based"
    assert executed.parsed_output["severity"] == "medium"


@pytest.mark.asyncio
async def test_retry_subagent_task(db_session: Session):
    run = AgentRun(user_request="测试重试", status="running")
    db_session.add(run)
    db_session.commit()

    service = SubAgentService(db_session)
    tasks = await service.create_tasks_from_plan(
        run_id=run.id,
        parent_step_id=None,
        task_specs=[{"task_type": "summary", "title": "汇总", "role": "planner"}],
    )
    task = tasks[0]
    task.status = SubAgentTaskStatus.FAILED
    task.error_message = "旧错误"
    db_session.commit()

    retried = await service.retry_task(task.id)

    assert retried.status == SubAgentTaskStatus.SUCCEEDED
    assert retried.error_message is None


def test_reduce_subagent_results(db_session: Session):
    run = AgentRun(user_request="测试汇总", status="running")
    db_session.add(run)
    db_session.commit()

    summary = SubAgentService(db_session).reduce_results(run.id)

    assert summary["run_id"] == run.id
    assert summary["total"] == 0
