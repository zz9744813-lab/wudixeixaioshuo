"""NovelForge AI - Router aggregation"""
from fastapi import APIRouter

from app.routers import health, setup, diagnostics

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(setup.router)
api_router.include_router(diagnostics.router)

__all__ = ["api_router"]
