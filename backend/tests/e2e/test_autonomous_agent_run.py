"""
E2E Test - 自主 Agent 运行端到端验收
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app


@pytest.fixture
def client(db_session):
    from app.database import get_db

    def override():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def api_key():
    return {"X-API-Key": "test-api-key-for-ci", "Content-Type": "application/json"}


def test_e2e_full_agent_run(client, api_key, db_session):
    """端到端测试：创建 agent_run → 生成 plan → 执行工具 → 落库步骤与报告。

    注意：/start 端点用 asyncio.create_task + 独立 SessionLocal 在后台执行，
    与测试事务连接隔离，无法在同一事务里观察到结果。因此此处直接通过
    service 层同步执行 execute_run，验证编排主流程真实落库。
    """
    import asyncio
    from app.services.orchestrator_service import OrchestratorService

    # 1. 启动 agent_run（走真实 API 创建记录）
    response = client.post(
        "/api/agent-runs",
        json={
            "user_request": "创建一部东方修仙系统流小说，面向起点读者，目标 200万字，日更 1 万。",
            "mode": "autonomous",
            "max_steps": 10,
        },
        headers=api_key,
    )
    assert response.status_code == 200
    run_id = response.json()["id"]
    assert response.json()["status"] == "pending"

    # 2. 同步执行编排（共享测试事务连接）
    service = OrchestratorService(db_session)
    asyncio.run(service.execute_run(run_id))

    # 3. 验证运行详情
    response = client.get(f"/api/agent-runs/{run_id}", headers=api_key)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == run_id
    assert data["status"] in ["succeeded", "failed", "paused"]

    # 4. 验证步骤已落库
    response = client.get(f"/api/agent-runs/{run_id}/steps", headers=api_key)
    assert response.status_code == 200
    steps = response.json()
    assert len(steps) > 0

    # 5. 验证事件已记录
    response = client.get(f"/api/agent-runs/{run_id}/events", headers=api_key)
    assert response.status_code == 200
    events = response.json()
    assert len(events) > 0

    # 6. 验证报告可读
    response = client.get(f"/api/agent-runs/{run_id}/report", headers=api_key)
    assert response.status_code == 200
    report = response.json()
    assert report["run_id"] == run_id

    # 7. 验证子 Agent 任务接口可达
    response = client.get(f"/api/subagents/tasks", params={"run_id": run_id}, headers=api_key)
    assert response.status_code == 200


def test_e2e_research_api(client, api_key):
    """端到端测试：研究 API 可达。"""
    response = client.get("/api/research/runs", headers=api_key)
    assert response.status_code == 200

    response = client.get("/api/research/patterns", headers=api_key)
    assert response.status_code == 200

    response = client.get("/api/research/reader-insights", headers=api_key)
    assert response.status_code == 200

    response = client.get("/api/research/trends", headers=api_key)
    assert response.status_code == 200


def test_e2e_evolution_api(client, api_key):
    """端到端测试：进化 API 可达。"""
    response = client.get("/api/evolution-auto/policies", headers=api_key)
    assert response.status_code == 200

    response = client.get("/api/evolution-auto/runs", headers=api_key)
    assert response.status_code == 200


def test_e2e_agent_run_cancel(client, api_key):
    """端到端测试：取消运行。"""
    response = client.post(
        "/api/agent-runs",
        json={"user_request": "测试取消", "mode": "autonomous"},
        headers=api_key,
    )
    run_id = response.json()["id"]

    response = client.post(f"/api/agent-runs/{run_id}/start", headers=api_key)
    assert response.status_code == 200

    response = client.post(f"/api/agent-runs/{run_id}/cancel", headers=api_key)
    assert response.status_code == 200
