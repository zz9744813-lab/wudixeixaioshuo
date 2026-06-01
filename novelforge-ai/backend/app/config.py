"""NovelForge AI - Settings"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_env: str = "development"
    secret_key: str = "dev-secret-key-change-in-production"
    cors_origins: str = "http://localhost:3005,http://127.0.0.1:3005"

    # Database
    database_url: str = "postgresql://novelforge:novelforge@localhost:5432/novelforge"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # API
    app_api_key: str = ""

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
