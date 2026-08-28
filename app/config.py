"""Application settings (pydantic-settings).

Reads from `.env` (see `.env.example`). The `DATABASE_URL` value selects the
backend: `sqlite:///...` for local smoke tests, `postgresql+psycopg2://...` for
production. SQLAlchemy 2.0 (sync engine) is used so the platform runs without
extra async drivers installed; the connection string is the single switch.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    app_name: str = "Novel Genome"
    schema_version: str = "1.0"
    environment: str = "local"
    database_url: str = "sqlite:///./novel_genome.db"
    log_level: str = "INFO"
    redis_url: str = ""
    broker_dsn: str = ""
    default_source_class: str = "human_original"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
