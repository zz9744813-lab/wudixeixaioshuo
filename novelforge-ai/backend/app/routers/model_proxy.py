"""NovelForge AI - Model proxy: forward /v1/chat/completions to configured provider."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.database import get_db
from app.services.llm_router import resolve_provider_and_model

router = APIRouter()
logger = logging.getLogger("novelforge.proxy")


@router.post("/v1/chat/completions")
async def proxy_chat_completions(request: Request, db: Any = Depends(get_db)):
    body = await request.json()
    role = body.get("role", "default")
    try:
        provider, model = resolve_provider_and_model(db, role)
    except Exception as exc:
        logger.exception("model proxy failed: %s", exc)
        return JSONResponse(status_code=502, content={"error": str(exc)})

    target = (provider.base_url or "http://localhost:8000").rstrip("/") + "/chat/completions"
    headers: dict[str, str] = {"Content-Type": "application/json"}
    # In real impl, decrypt api_key and set Authorization header here

    try:
        import httpx

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(target, json=body, headers=headers)
            return JSONResponse(status_code=resp.status_code, content=resp.json())
    except Exception as exc:
        logger.exception("model proxy upstream failed: %s", exc)
        return JSONResponse(status_code=502, content={"error": str(exc)})
