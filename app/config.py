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

    # LLM layer (EPIC-C+). OpenAI-compatible. Left empty -> deterministic FakeProvider.
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    # Force the deterministic fake provider even if a key is set (tests / offline).
    force_fake_llm: bool = False

    # CORS allowlist (comma-separated). "*" only if explicitly configured.
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Redis-backed queue (optional; empty = local queue only)
    # redis_url already defined above.


    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
