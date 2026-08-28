"""Provider selection (spec §29 router).

Picks the provider for an Agent run. Priority: ``force_fake_llm`` -> no key ->
``FakeProvider``; otherwise ``OpenAICompatibleProvider`` (per ModelRegistry row
when provided, else settings).
"""
from __future__ import annotations

from typing import Optional

from app.config import get_settings
from app.llm.fake import FakeProvider
from app.llm.openai_compat import OpenAICompatibleProvider
from app.llm.provider import LLMProvider


def get_provider(db=None, model_registry_id: Optional[str] = None) -> LLMProvider:
    s = get_settings()
    if s.force_fake_llm:
        return FakeProvider(db=db)
    if not (s.llm_base_url and s.llm_api_key and s.llm_model):
        return FakeProvider(db=db)
    return OpenAICompatibleProvider()
