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
