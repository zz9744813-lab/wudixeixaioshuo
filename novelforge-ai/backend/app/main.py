"""NovelForge AI - FastAPI entry"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import engine
from app.errors import NovelForgeError
from app.models.entities import Base
from app.routers import api_router



@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="NovelForge AI",
    description="NovelForge AI API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(NovelForgeError)
async def app_error_handler(request, exc: NovelForgeError):
    return JSONResponse(
        status_code=exc.status,
        content={
            "ok": False,
            "code": exc.code,
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "ok": False,
            "code": "validation_error",
            "message": "Invalid request",
            "details": {"errors": exc.errors()},
        },
    )


app.include_router(api_router, prefix="/api")
