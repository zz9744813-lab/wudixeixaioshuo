"""
Auth Dependencies - API Key 鉴权
"""

import hmac
import secrets
from fastapi import Header, HTTPException, status


def get_api_key_from_env():
    """从环境变量读取 API Key"""
    import os
    return os.getenv("APP_API_KEY", "")


def require_api_key(x_api_key: str = Header(default="", alias="X-API-Key")):
    """
    要求请求携带有效的 API Key

    - 从环境变量 APP_API_KEY 读取预期值
    - 生产环境必须配置 APP_API_KEY，否则拒绝服务
    - 使用 hmac.compare_digest 防止时序攻击
    """
    expected_key = get_api_key_from_env()

    # 生产环境必须配置 API Key
    if not expected_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="APP_API_KEY is not configured on server",
        )

    # 检查请求是否携带 Key
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # 使用 hmac.compare_digest 防止时序攻击
    if not hmac.compare_digest(x_api_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return x_api_key


def require_api_key_optional(x_api_key: str = Header(default="", alias="X-API-Key")):
    """
    可选鉴权 - 用于健康检查等公开端点
    如果配置了 APP_API_KEY 则验证，否则放行
    """
    expected_key = get_api_key_from_env()

    if not expected_key:
        # 未配置 Key，允许访问
        return None

    if x_api_key and hmac.compare_digest(x_api_key, expected_key):
        return x_api_key

    # 配置了 Key 但请求没带或带错
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API key",
        headers={"WWW-Authenticate": "ApiKey"},
    )
