"""LLM layer (EPIC-C+).

A small provider abstraction so every analysis Agent talks to *one* interface
and every call is traced. Two implementations ship:

* :class:`FakeProvider` — deterministic, schema-shaped output. Used when no API
  key is configured (offline / CI) and in tests, so the full multi-pass
  pipeline runs end-to-end without a real model (spec §39 "本地用 SQLite 直接跑通").
* :class:`OpenAICompatibleProvider` — calls any OpenAI-compatible
  ``/chat/completions`` endpoint (OpenAI / DeepSeek / local vLLM / ...).

:func:`get_provider` picks based on settings (``force_fake_llm`` or missing key).
"""
from __future__ import annotations

from app.llm.factory import get_provider
from app.llm.fake import FakeProvider
from app.llm.openai_compat import OpenAICompatibleProvider
from app.llm.provider import LLMMessage, LLMProvider, extract_json

__all__ = [
    "LLMProvider",
    "LLMMessage",
    "FakeProvider",
    "OpenAICompatibleProvider",
    "get_provider",
    "extract_json",
]
