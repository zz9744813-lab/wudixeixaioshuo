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


def test_sse_stream_with_api_key_header_returns_200(client, api_headers, monkeypatch):
    """SSE /api/events/stream 在 APP_API_KEY 配置 + X-API-Key header 时应返回 200"""
    monkeypatch.setenv("APP_API_KEY", "test-secret-key")
    headers = {"X-API-Key": "test-secret-key"}
    # SSE endpoint 返回 200 并建立流连接
    response = client.get("/api/events/stream", headers=headers)
    assert response.status_code == 200


def test_sse_stream_without_auth_returns_401(client, monkeypatch):
    """SSE /api/events/stream 未提供 API Key 时应返回 401"""
    monkeypatch.setenv("APP_API_KEY", "test-secret-key")
    response = client.get("/api/events/stream")
    assert response.status_code == 401
