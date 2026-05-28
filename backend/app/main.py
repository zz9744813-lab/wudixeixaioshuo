"""
Novel Agent System - Main Application
24小时小说 Agent 工作台 - 主应用入口
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import engine, init_db
from app.routers import (
    agents,
    bible,
    books,
    chapters,
    dashboard,
    evolution,
    export,
    feedback,
    health,
    memory,
    models,
    projects,
    skills,  # P4 Phase 2
    tasks,
    techniques,
    worker,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    init_db()
    yield
    # 关闭时清理资源


app = FastAPI(
    title="24小时小说 Agent 工作台",
    description="拆书学习 + 自动写作 + 自我进化的小说创作系统",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health.router, prefix="/api/health", tags=["Health"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(chapters.router, prefix="/api", tags=["Chapters"])
app.include_router(books.router, prefix="/api/books", tags=["Books"])
app.include_router(techniques.router, prefix="/api/techniques", tags=["Techniques"])
app.include_router(skills.router, prefix="/api/skills", tags=["Skills"])  # P4 Phase 2
app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"])
app.include_router(agents.router, prefix="/api/agents", tags=["Agents"])
app.include_router(models.router, prefix="/api/models", tags=["Models"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["Feedback"])
app.include_router(evolution.router, prefix="/api/evolution", tags=["Evolution"])
app.include_router(bible.router, prefix="/api", tags=["Bible"])
app.include_router(worker.router, prefix="/api/worker", tags=["Worker"])
app.include_router(memory.router, prefix="/api/memory", tags=["Memory"])  # P4: 记忆系统
app.include_router(export.router, prefix="/api/export", tags=["Export"])


@app.get("/")
async def root():
    return {
        "message": "24小时小说 Agent 工作台 API",
        "version": "0.1.0",
        "docs": "/docs",
    }
