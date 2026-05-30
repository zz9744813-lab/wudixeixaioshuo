"""
Novel Agent System - Main Application
24小时小说 Agent 工作台 - 主应用入口
"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import engine, init_db
from app.deps.auth import require_api_key
from app.middleware import setup_exception_handlers, LoggingMiddleware
from app.routers import (
    agents,
    bible,
    books,
    chapters,
    cover,
    dashboard,
    events,
    evolution,
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
    review,
    reviews,
    skills,
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
    # 启动时初始化
    setup_logging()
    init_db()
    yield
    # 关闭时清理资源
    await llm_manager.close_all()


app = FastAPI(
    title="24小时小说 Agent 工作台",
    description="拆书学习 + 自动写作 + 自我进化的小说创作系统",
    version="0.1.0",
    lifespan=lifespan,
)

# 设置全局异常处理器
setup_exception_handlers(app)

# 添加日志中间件
app.add_middleware(LoggingMiddleware)

# CORS 配置 - 从配置中心读取
CORS_ORIGINS = settings.CORS_ORIGINS.split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由 - 健康检查无需鉴权
app.include_router(health.router, prefix="/api/health", tags=["Health"])

# 业务路由需要鉴权
app.include_router(
    dashboard.router,
    prefix="/api/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(require_api_key)],
)
app.include_router(
    projects.router,
    prefix="/api/projects",
    tags=["Projects"],
    dependencies=[Depends(require_api_key)],
)
app.include_router(
    chapters.router,
    prefix="/api",
    tags=["Chapters"],
    dependencies=[Depends(require_api_key)],
)
app.include_router(
    books.router,
    prefix="/api/books",
    tags=["Books"],
    dependencies=[Depends(require_api_key)],
)
app.include_router(
    techniques.router,
    prefix="/api/techniques",
    tags=["Techniques"],
    dependencies=[Depends(require_api_key)],
)
app.include_router(
    skills.router,
    prefix="/api/skills",
    tags=["Skills"],
    dependencies=[Depends(require_api_key)],
)
app.include_router(
    foreshadows.router,
    prefix="/api/foreshadows",
    tags=["Foreshadows"],
    dependencies=[Depends(require_api_key)],
)
app.include_router(
    reviews.router,
    prefix="/api/reviews",
    tags=["Reviews"],
    dependencies=[Depends(require_api_key)],
)
app.include_router(
    production.router,
    prefix="/api/production",
    tags=["Production"],
    dependencies=[Depends(require_api_key)],
)
app.include_router(
    tasks.router,
    prefix="/api/tasks",
    tags=["Tasks"],
    dependencies=[Depends(require_api_key)],
)
app.include_router(
    agents.router,
    prefix="/api/agents",
    tags=["Agents"],
    dependencies=[Depends(require_api_key)],
)
app.include_router(
    models.router,
    prefix="/api/models",
    tags=["Models"],
    dependencies=[Depends(require_api_key)],
)
app.include_router(
    llm_routes.router,
    prefix="/api/llm-routes",
    tags=["LLM Routes"],
    dependencies=[Depends(require_api_key)],
)
app.include_router(
    feedback.router,
    prefix="/api/feedback",
    tags=["Feedback"],
    dependencies=[Depends(require_api_key)],
)
app.include_router(
    evolution.router,
    prefix="/api/evolution",
    tags=["Evolution"],
    dependencies=[Depends(require_api_key)],
)
app.include_router(
    bible.router,
    prefix="/api",
    tags=["Bible"],
    dependencies=[Depends(require_api_key)],
)
app.include_router(
    worker.router,
    prefix="/api/worker",
    tags=["Worker"],
    dependencies=[Depends(require_api_key)],
)
app.include_router(
    memory.router,
    prefix="/api/memory",
    tags=["Memory"],
    dependencies=[Depends(require_api_key)],
)
app.include_router(
    export.router,
    prefix="/api/export",
    tags=["Export"],
    dependencies=[Depends(require_api_key)],
)
app.include_router(
    usage.router,
    prefix="/api/usage",
    tags=["Usage"],
    dependencies=[Depends(require_api_key)],
)
app.include_router(
    events.router,
    prefix="/api/events",
    tags=["Events"],
    # 注意：SSE端点在内部自行验证API Key（支持header或query），不在路由级验证
)
app.include_router(
    prompts.router,
    prefix="/api/prompts",
    tags=["Prompts"],
    dependencies=[Depends(require_api_key)],
)
app.include_router(
    review.router,
    prefix="/api/review",
    tags=["Review"],
    dependencies=[Depends(require_api_key)],
)
app.include_router(
    cover.router,
    prefix="/api/covers",
    tags=["Covers"],
    dependencies=[Depends(require_api_key)],
)


@app.get("/")
async def root():
    return {
        "message": "24小时小说 Agent 工作台 API",
        "version": "0.1.0",
        "docs": "/docs",
    }
