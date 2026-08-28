"""OpenAI-compatible chat provider (spec §29).

Calls any ``/chat/completions`` endpoint with only the standard library
(``urllib`` + ``json``) so no extra dependency is required. Reads base url / key
/ model from settings. Raises ``RuntimeError`` if not configured — the caller
should fall back to :class:`FakeProvider` in that case.
"""
from __future__ import annotations

import json
import urllib.request
from typing import List, Optional, Type

from pydantic import BaseModel

from app.config import get_settings
from app.llm.provider import LLMMessage


class OpenAICompatibleProvider:
    name = "openai_compatible"

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 300.0,
        max_retries: int = 2,
    ) -> None:
        s = get_settings()
        self.base_url = (base_url or s.llm_base_url or "").rstrip("/")
        self.api_key = api_key or s.llm_api_key or ""
        self.model = model or s.llm_model or ""
        self.timeout = timeout
        self.max_retries = max_retries
        if not self.base_url or not self.api_key or not self.model:
            raise RuntimeError(
                "OpenAICompatibleProvider not configured: set NOVEL_GENOME_LLM_BASE_URL / "
                "NOVEL_GENOME_LLM_API_KEY / NOVEL_GENOME_LLM_MODEL (or leave empty to use FakeProvider)"
            )

    def complete(
        self,
        messages: List[LLMMessage],
        *,
        output_model: Optional[Type[BaseModel]] = None,
        temperature: float = 0.2,
        **kwargs,
    ) -> str:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [m.model_dump() for m in messages],
            "temperature": temperature,
            "response_format": {"type": "json_object"} if output_model is not None else None,
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        # Bounded retry on transient failures (timeout / 429 / 5xx) — never
        # infinite (禁止11): at most ``max_retries`` extra attempts.
        import time

        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                return body["choices"][0]["message"]["content"]
            except urllib.error.HTTPError as exc:
                if exc.code == 429 or exc.code >= 500:
                    last_exc = exc
                else:
                    raise  # 4xx (except 429) is a caller error, not transient
            except (TimeoutError, urllib.error.URLError) as exc:
                last_exc = exc
            if attempt < self.max_retries:
                time.sleep(2.0 * (2 ** attempt))
        raise last_exc  # type: ignore[misc]
