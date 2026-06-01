"""NovelForge AI - Router aggregation"""
from fastapi import APIRouter

from . import auth, events, health, setup, diagnostics, projects, chapters

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(setup.router)
api_router.include_router(diagnostics.router)
api_router.include_router(projects.router)
api_router.include_router(chapters.router)
api_router.include_router(auth.router)
api_router.include_router(events.router, prefix="/api")
