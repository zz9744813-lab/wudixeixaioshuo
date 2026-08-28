"""FastAPI application entrypoint for Novel Genome (Stage 0 / EPIC-A)."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db import Base, init_db, get_engine
from app import models  # noqa: F401  (register tables on Base.metadata)

configure_logging()
logger = get_logger("novel_genome.main")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Novel Genome %s starting (env=%s)", settings.schema_version, settings.environment)
    # Dev convenience: ensure tables exist. In production Alembic owns the schema.
    if settings.environment in ("local", "test"):
        try:
            init_db()
            logger.info("Ensured local tables via metadata.create_all")
        except Exception as exc:  # pragma: no cover
            logger.warning("create_all skipped: %s", exc)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.schema_version,
    description="Computational Narrative Science & Story World Modeling Platform",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api import corpus, scene, character, research, knowledge, novelforge, ingest  # noqa: E402

for r in (corpus, scene, character, research, knowledge, novelforge, ingest):
    app.include_router(r.router)


@app.get("/health", tags=["meta"])
def health():
    from sqlalchemy import inspect
    table_count = len(inspect(get_engine()).get_table_names())
    return {
        "app": settings.app_name,
        "status": "ok",
        "schema_version": settings.schema_version,
        "tables": table_count,
    }


@app.get("/", tags=["meta"])
def root():
    return {"app": settings.app_name, "docs": "/docs", "health": "/health"}
