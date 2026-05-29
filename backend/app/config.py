"""
App Config - 统一配置中心
"""

import os
from functools import lru_cache
from pathlib import Path

from pydantic import model_validator, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""

    # 环境
    APP_ENV: str = "development"
    APP_DEBUG: bool = False

    # 安全 - 生产环境必须配置
    APP_API_KEY: str = ""  # 必须配置，生产环境不能为空
    APP_SECRET_KEY: str = ""  # 用于加密等

    # 数据库
    DATABASE_URL: str = ""

    # 上传
    UPLOAD_DIR: str = ""
    MAX_UPLOAD_BYTES: int = 50 * 1024 * 1024  # 50MB

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173"

    # 日志
    LOG_LEVEL: str = "INFO"

    # 时区
    DEFAULT_TIMEZONE: str = "UTC"

    # 开发环境自动创建表（生产环境禁用）
    APP_AUTO_CREATE_TABLES: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @model_validator(mode="after")
    def validate_required_secrets(self):
        """
        Fail-Fast: 生产/预发环境必须配置 APP_API_KEY 和 APP_SECRET_KEY
        """
        env = (self.APP_ENV or "").lower()
        if env in {"production", "prod", "staging"}:
            missing = []
            if not self.APP_API_KEY:
                missing.append("APP_API_KEY")
            if not self.APP_SECRET_KEY:
                missing.append("APP_SECRET_KEY")
            if missing:
                raise ValueError(
                    f"🚨 [BE-001] 生产环境必须设置 {', '.join(missing)}！\n"
                    f"当前环境: {self.APP_ENV}\n"
                    f"请设置环境变量: export {' '.join(f'{k}=your-secure-key' for k in missing)}\n"
                    f"或创建 .env 文件并配置"
                )
        return self


@lru_cache()
def get_settings() -> Settings:
    """获取配置（缓存）"""
    settings = Settings()

    # 设置默认值
    if not settings.DATABASE_URL:
        default_db_path = Path(__file__).parent.parent / "data" / "novel_agent.db"
        default_db_path.parent.mkdir(parents=True, exist_ok=True)
        settings.DATABASE_URL = f"sqlite:///{default_db_path}"

    if not settings.UPLOAD_DIR:
        upload_path = Path(__file__).parent.parent / "data" / "uploads"
        upload_path.mkdir(parents=True, exist_ok=True)
        settings.UPLOAD_DIR = str(upload_path)

    return settings


settings = get_settings()
