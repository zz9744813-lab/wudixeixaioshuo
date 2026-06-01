"""NovelForge AI - LLM router: provider resolution, key management, fallback."""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.models.entities import ModelProvider, ModelRoute
from app.services.llm_service import generate_text

logger = logging.getLogger("novelforge.llm")


class LLMProviderError(Exception):
    pass


def _decrypt(encrypted: str) -> str:
    """
    P0 decrypt stub. Real implementation uses app.secret_key via Fernet.
    """
    if not encrypted:
        raise LLMProviderError("empty api key")
    return encrypted


def resolve_provider_and_model(db: Session, role: str) -> tuple[ModelProvider, str]:
    """
    Return (provider, model_name) for a given role, falling back to the first
    enabled provider if no route matches.
    """
    route = (
        db.query(ModelRoute)
        .filter(ModelRoute.role == role, ModelRoute.enabled == 1)
        .first()
    )
    if route:
        provider = db.get(ModelProvider, route.primary_provider_id)
        if provider and provider.enabled == 1:
            return provider, route.primary_model
        if route.fallback_provider_id:
            fallback = db.get(ModelProvider, route.fallback_provider_id)
            if fallback and fallback.enabled == 1:
                return fallback, route.fallback_model or route.primary_model

    provider = db.query(ModelProvider).filter(ModelProvider.enabled == 1).first()
    if not provider:
        raise LLMProviderError(f"No enabled ModelProvider configured for role={role}")
    return provider, provider.default_model or "gpt-3.5-turbo"


async def call_llm(
    db: Session,
    *,
    role: str,
    prompt: str,
    max_tokens: int = 512,
    temperature: float = 0.7,
) -> dict[str, Any]:
    provider, model = resolve_provider_and_model(db, role)
    api_key = _decrypt(provider.api_key_encrypted)

    try:
        result = await generate_text(
            prompt=prompt,
            model=model,
            api_key=api_key,
            base_url=provider.base_url,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        logger.info("llm_call ok role=%s provider=%s model=%s", role, provider.name, model)
        return result
    except Exception as exc:
        logger.exception("llm_call failed role=%s provider=%s model=%s", role, provider.name, model)
        raise LLMProviderError(str(exc)) from exc
