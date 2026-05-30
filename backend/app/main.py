"""
Novel Agent System - Main Application
24小时小说 Agent 工作台 - 主应用入口
"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.deps.auth import require_api_key
from app.middleware import LoggingMiddleware, setup_exception_handlers
from app.routers import (
    agent_runs,
    agents,
    bible,
    books,
    chapters,
    cover,
    dashboard,
    events,
    evolution,
    evolution_auto,
    export,
    feedback,
    foreshadows,
    health,
    llm_routes,
    memory,
    models,
    production,
    projects,
    prompts,
    research,
    review,
    reviews,
    skills,
    subagents,
    tasks,
    techniques,
    usage,
    worker,
)
from app.services.openai_llm_service import llm_manager
from app.utils.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    setup_logging()
    init_db()
    yield
    await llm_manager.close_all()


app = FastAPI(
    title="24小时小说 Agent 工作台",
    description="拆书学习 + 自动写作 + 自我进化的小说创作系统",
    version="0.1.0",
    lifespan=lifespan,
)

setup_exception_handlers(app)
app.add_middleware(LoggingMiddleware)

CORS_ORIGINS = settings.CORS_ORIGINS.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/health", tags=["Health"])

PROTECTED = [Depends(require_api_key)]

app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"], dependencies=PROTECTED)
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"], dependencies=PROTECTED)
app.include_router(chapters.router, prefix="/api", tags=["Chapters"], dependencies=PROTECTED)
app.include_router(books.router, prefix="/api/books", tags=["Books"], dependencies=PROTECTED)
app.include_router(techniques.router, prefix="/api/techniques", tags=["Techniques"], dependencies=PROTECTED)
app.include_router(skills.router, prefix="/api/skills", tags=["Skills"], dependencies=PROTECTED)
app.include_router(foreshadows.router, prefix="/api/foreshadows", tags=["Foreshadows"], dependencies=PROTECTED)
app.include_router(reviews.router, prefix="/api/reviews", tags=["Reviews"], dependencies=PROTECTED)
app.include_router(production.router, prefix="/api/production", tags=["Production"], dependencies=PROTECTED)
app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"], dependencies=PROTECTED)
app.include_router(agents.router, prefix="/api/agents", tags=["Agents"], dependencies=PROTECTED)
app.include_router(agent_runs.router, prefix="/api", tags=["Agent Runs"], dependencies=PROTECTED)
app.include_router(subagents.router, prefix="/api", tags=["SubAgents"], dependencies=PROTECTED)
app.include_router(models.router, prefix="/api/models", tags=["Models"], dependencies=PROTECTED)
app.include_router(llm_routes.router, prefix="/api/llm-routes", tags=["LLM Routes"], dependencies=PROTECTED)
app.include_router(feedback.router, prefix="/api/feedback", tags=["Feedback"], dependencies=PROTECTED)
app.include_router(evolution.router, prefix="/api/evolution", tags=["Evolution"], dependencies=PROTECTED)
app.include_router(bible.router, prefix="/api", tags=["Bible"], dependencies=PROTECTED)
app.include_router(worker.router, prefix="/api/worker", tags=["Worker"], dependencies=PROTECTED)
app.include_router(memory.router, prefix="/api/memory", tags=["Memory"], dependencies=PROTECTED)
app.include_router(export.router, prefix="/api/export", tags=["Export"], dependencies=PROTECTED)
app.include_router(usage.router, prefix="/api/usage", tags=["Usage"], dependencies=PROTECTED)
app.include_router(prompts.router, prefix="/api/prompts", tags=["Prompts"], dependencies=PROTECTED)
app.include_router(review.router, prefix="/api/review", tags=["Review"], dependencies=PROTECTED)
app.include_router(cover.router, prefix="/api/covers", tags=["Covers"], dependencies=PROTECTED)
app.include_router(research.router, prefix="/api", tags=["Research"], dependencies=PROTECTED)
app.include_router(evolution_auto.router, prefix="/api", tags=["Evolution Auto"], dependencies=PROTECTED)

# SSE 端点内部自行验证 API Key，支持 Header 或 query 参数。
app.include_router(events.router, prefix="/api/events", tags=["Events"])


@app.get("/")
async def root():
    return {
        "message": "24小时小说 Agent 工作台 API",
        "version": "0.1.0",
        "docs": "/docs",
    }
