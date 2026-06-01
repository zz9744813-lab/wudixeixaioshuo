"""NovelForge AI - Router aggregation"""
from fastapi import APIRouter

from . import agent_runs, auth, bible, events, export, foreshadow, health, memory, outline, projects, setup, diagnostics, chapters, model_proxy

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(setup.router)
api_router.include_router(diagnostics.router)
api_router.include_router(projects.router)
api_router.include_router(chapters.router)
api_router.include_router(auth.router)
api_router.include_router(agent_runs.router)
api_router.include_router(model_proxy.router)
api_router.include_router(bible.router)
api_router.include_router(outline.router)
api_router.include_router(memory.router)
api_router.include_router(foreshadow.router)
api_router.include_router(export.router)
api_router.include_router(events.router)
