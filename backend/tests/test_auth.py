"""
Auth Tests
鉴权测试
"""

import pytest


def test_business_api_without_auth_returns_401(client):
    """业务接口无鉴权应返回 401"""
    # 不带 X-API-Key 的请求
    response = client.get("/api/projects/")
    assert response.status_code == 401


def test_business_api_with_wrong_key_returns_401(client):
    """业务接口错误鉴权应返回 401"""
    headers = {"X-API-Key": "wrong-key"}
    response = client.get("/api/projects/", headers=headers)
    assert response.status_code == 401


def test_business_api_with_correct_key_success(client, api_headers):
    """业务接口正确鉴权应正常访问"""
    response = client.get("/api/projects/", headers=api_headers)
    assert response.status_code == 200


def test_worker_control_without_auth_returns_401(client):
    """Worker控制接口无鉴权应返回 401"""
    response = client.post("/api/worker/control", json={"action": "status"})
    assert response.status_code == 401


def test_sse_stream_with_api_key_header_returns_200(monkeypatch):
    """SSE 鉴权：配置 APP_API_KEY 且提供正确 X-API-Key header 时，鉴权依赖应放行。

    不真实打开无限事件流（会阻塞在 queue.get 导致 TestClient 关闭挂起），
    直接验证鉴权依赖 validate_api_key 的放行逻辑。
    """
    from unittest.mock import MagicMock
    from app.routers.events import validate_api_key

    monkeypatch.setenv("APP_API_KEY", "test-secret-key")
    request = MagicMock()
    request.headers = {"X-API-Key": "test-secret-key"}
    assert validate_api_key(request, api_key="") is True


def test_sse_stream_without_auth_returns_401(client, monkeypatch):
    """SSE /api/events/stream 未提供 API Key 时应返回 401"""
    monkeypatch.setenv("APP_API_KEY", "test-secret-key")
    response = client.get("/api/events/stream")
    assert response.status_code == 401
