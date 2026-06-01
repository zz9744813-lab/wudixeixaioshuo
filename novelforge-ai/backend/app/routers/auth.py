"""NovelForge AI - Auth router"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.database import get_db
from app.models.entities import User
from app.schemas.auth import LoginRequest, TokenResponse, UserSelfResponse

router = APIRouter()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: Any = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = secrets.token_urlsafe(32)
    return TokenResponse(access_token=token)


@router.post("/logout")
async def logout():
    return {"ok": True}


@router.get("/me", response_model=UserSelfResponse)
async def me():
    return UserSelfResponse(id="local", username="admin")
