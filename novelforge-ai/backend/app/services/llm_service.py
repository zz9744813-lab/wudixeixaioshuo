"""NovelForge AI - LLM service placeholder"""
from __future__ import annotations

from typing import Any

import httpx

from app.config import settings


class LLMServiceError(Exception):
    pass


async def generate_text(
    *,
    prompt: str,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    max_tokens: int = 512,
    temperature: float = 0.7,
) -> dict[str, Any]:
    """
    Thin wrapper around an OpenAI-compatible /chat/completions endpoint.
    Real provider-specific auth and fallback logic will be added in P2.
    """
    url = (base_url or "http://localhost:8000/v1").rstrip("/") + "/chat/completions"
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model or "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        choice = data["choices"][0]["message"]
        usage = data.get("usage", {})
        return {
            "content": choice["content"],
            "model": data.get("model", model),
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
        }
