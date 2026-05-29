"""
Health Check Tests
健康检查测试
"""

import pytest


def test_health_check_success(client):
    """健康检查 - 无鉴权应返回 200"""
    response = client.get("/api/health/")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] in ["healthy", "unhealthy"]
    assert data["service"] == "24小时小说 Agent 工作台"
    assert "version" in data
    assert "database" in data


def test_health_check_no_auth_required(client):
    """健康检查 - 不需要鉴权"""
    response = client.get("/api/health/")
    assert response.status_code == 200
    assert "status" in response.json()
