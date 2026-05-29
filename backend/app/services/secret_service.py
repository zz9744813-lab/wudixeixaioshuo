"""
Secret Service - API Key 加密/解密工具
"""

import logging
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    key = os.getenv("APP_SECRET_KEY")
    if not key:
        raise RuntimeError(
            "APP_SECRET_KEY 未配置。请使用："
            "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\" "
            "生成密钥，并写入环境变量。"
        )

    try:
        return Fernet(key.encode())
    except Exception as exc:
        raise RuntimeError(
            "APP_SECRET_KEY 格式无效。必须是 Fernet.generate_key() 生成的 urlsafe base64 key。"
        ) from exc


def encrypt_api_key(api_key: Optional[str]) -> Optional[str]:
    if not api_key:
        return None
    fernet = _get_fernet()
    return fernet.encrypt(api_key.encode("utf-8")).decode("utf-8")


def decrypt_api_key(value: Optional[str]) -> str:
    """
    解密 API Key。

    兼容老数据：
    - 新数据：Fernet token，正常解密。
    - 老数据：明文 key，解密失败时原样返回，但打 warning。
    """
    if not value:
        return ""

    # 先检查是否是明文（不以 Fernet 的 gAAAA 开头）
    # Fernet token 格式：gAAAA...
    if not value.startswith("gAAAA"):
        # 可能是旧版明文数据
        logger.warning("检测到旧版明文 API Key，请重新保存模型配置以完成加密迁移。")
        return value

    # 需要解密
    fernet = _get_fernet()

    try:
        return fernet.decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        # 解密失败，可能是损坏的数据
        logger.error("API Key 解密失败，数据可能已损坏。")
        raise ValueError("API Key 解密失败，请重新配置模型提供商。")


def mask_api_key(api_key: Optional[str]) -> Optional[str]:
    if not api_key:
        return None
    tail = api_key[-4:] if len(api_key) >= 4 else api_key
    return f"****{tail}"
