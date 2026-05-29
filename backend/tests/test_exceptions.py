"""
Exception Handler Tests
异常处理测试
"""

import pytest
from fastapi.testclient import TestClient

from app.exceptions import (
    ValidationError,
    NotFoundError,
    ConflictError,
    PermissionError,
    RateLimitError,
    ExternalServiceError,
)


def test_validation_error_format(client: TestClient, api_headers):
    """验证错误应返回标准格式"""
    # 发送无效参数
    response = client.post(
        "/api/projects/",
        headers=api_headers,
        json={"name": ""}  # 空名称应触发验证错误
    )

    # 验证错误响应格式
    assert response.status_code in [400, 422]
    data = response.json()
    assert "detail" in data or "error" in data


def test_not_found_error_format(client: TestClient, api_headers):
    """资源不存在应返回 404"""
    response = client.get(
        "/api/projects/999999",  # 不存在的ID
        headers=api_headers
    )

    assert response.status_code == 404


def test_error_response_structure(client: TestClient, api_headers):
    """错误响应应具有标准结构"""
    # 触发一个验证错误
    response = client.post(
        "/api/worker/control",
        headers=api_headers,
        json={"action": "invalid_action"}
    )

    assert response.status_code == 400
    data = response.json()

    # 验证错误结构
    assert "detail" in data


def test_exception_to_dict():
    """测试异常转换为字典"""
    exc = ValidationError(
        message="字段验证失败",
        details={"field": "name", "error": "不能为空"}
    )

    data = exc.to_dict()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert data["error"]["message"] == "字段验证失败"
    assert data["error"]["details"]["field"] == "name"


def test_not_found_exception():
    """测试 NotFoundError"""
    exc = NotFoundError(
        message="Project with id 123 not found",
        details={"resource": "Project", "resource_id": 123}
    )
    assert exc.status_code == 404
    assert exc.error_code == "NOT_FOUND"
    assert "123" in exc.message


def test_permission_exception():
    """测试 PermissionError"""
    exc = PermissionError(
        message="Permission denied to delete Project",
        details={"action": "delete", "resource": "Project"}
    )
    assert exc.status_code == 403
    assert exc.error_code == "FORBIDDEN"


def test_rate_limit_exception():
    """测试 RateLimitError"""
    exc = RateLimitError(
        message="Too many requests, retry after 60 seconds",
        details={"retry_after": 60}
    )
    assert exc.status_code == 429
    assert exc.error_code == "RATE_LIMITED"


def test_external_service_exception():
    """测试 ExternalServiceError"""
    exc = ExternalServiceError(
        message="OpenAI API timeout",
        details={"service": "OpenAI"}
    )
    assert exc.status_code == 502
    assert exc.error_code == "EXTERNAL_SERVICE_ERROR"
