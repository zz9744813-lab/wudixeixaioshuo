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


def test_e2e_full_agent_run(client, api_key):
    """端到端测试：创建 provider route → 启动 agent_run → 生成 plan → 执行工具 → 生成报告。"""

    # 1. 创建 provider route（需要先有 provider）
    # 使用已有的 model_providers 或跳过此步

    # 2. 启动 agent_run
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
    run_id = response.data["id"]
    assert response.data["status"] == "pending"

    # 3. 启动执行
    response = client.post(f"/api/agent-runs/{run_id}/start", headers=api_key)
    assert response.status_code == 200

    # 4. 等待执行完成（轮询）
    import time
    for _ in range(30):
        time.sleep(0.5)
        response = client.get(f"/api/agent-runs/{run_id}", headers=api_key)
        if response.json()["status"] in ["succeeded", "failed", "paused"]:
            break

    # 5. 获取运行详情
    response = client.get(f"/api/agent-runs/{run_id}", headers=api_key)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == run_id

    # 6. 验证步骤已生成
    response = client.get(f"/api/agent-runs/{run_id}/steps", headers=api_key)
    assert response.status_code == 200
    steps = response.json()
    assert len(steps) > 0

    # 7. 验证事件已记录
    response = client.get(f"/api/agent-runs/{run_id}/events", headers=api_key)
    assert response.status_code == 200
    events = response.json()
    assert len(events) > 0

    # 8. 验证报告已生成
    response = client.get(f"/api/agent-runs/{run_id}/report", headers=api_key)
    assert response.status_code == 200
    report = response.json()
    assert report["run_id"] == run_id

    # 9. 验证子 Agent 任务
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
    run_id = response.data["id"]

    response = client.post(f"/api/agent-runs/{run_id}/start", headers=api_key)
    assert response.status_code == 200

    response = client.post(f"/api/agent-runs/{run_id}/cancel", headers=api_key)
    assert response.status_code == 200
