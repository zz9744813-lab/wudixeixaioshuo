"""
P0-3 接口冒烟测试
确认核心 worker/production 接口在正常数据下不返回 500。
"""

from sqlalchemy.orm import Session

from app.models.project import Project


def test_worker_status_not_500(client, api_headers):
    resp = client.get("/api/worker/status", headers=api_headers)
    assert resp.status_code == 200


def test_worker_reset_stats_not_500(client, api_headers):
    resp = client.post("/api/worker/reset-stats", headers=api_headers)
    assert resp.status_code == 200


def test_production_queue_not_500(client, api_headers):
    resp = client.get("/api/production/queue", headers=api_headers)
    assert resp.status_code == 200


def test_production_project_stats_not_500(client, api_headers, db_session: Session):
    project = Project(name="Stats Project", genre="玄幻", status="active")
    db_session.add(project)
    db_session.commit()

    resp = client.get(f"/api/production/projects/{project.id}/stats", headers=api_headers)
    assert resp.status_code == 200


def test_production_project_logs_not_500(client, api_headers, db_session: Session):
    project = Project(name="Logs Project", genre="玄幻", status="active")
    db_session.add(project)
    db_session.commit()

    resp = client.get(f"/api/production/projects/{project.id}/logs", headers=api_headers)
    assert resp.status_code == 200
