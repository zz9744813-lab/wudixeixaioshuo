"""NovelForge AI - Agent pipeline stubs"""
from __future__ import annotations

from typing import Any


def run_planner(*, project_id: str, chapter_index: int, context: dict[str, Any]) -> dict[str, Any]:
    # P1 stub: return a fixed plan object
    return {
        "chapter_index": chapter_index,
        "title": "未命名章节",
        "summary": "（计划阶段占位）",
        "plot_points": [],
        "characters": [],
        "target_words": 3000,
        "style_notes": "",
    }


def run_drafter(*, plan: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    return {
        "content": "（起草阶段占位）",
        "word_count": 0,
        "model": "",
        "input_tokens": 0,
        "output_tokens": 0,
    }


def run_critic(*, content: str, plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "score": 0.0,
        "dimensions": {},
        "issues": [],
        "suggestions": [],
    }


def run_rewriter(*, content: str, plan: dict[str, Any], critic: dict[str, Any]) -> dict[str, Any]:
    return {
        "content": content,
        "word_count": len(content),
        "changed": False,
    }


def run_continuity_checker(*, content: str, project_id: str, chapter_index: int) -> dict[str, Any]:
    return {
        "score": 0.0,
        "issues": [],
        "continuity_ok": True,
    }


def run_memory_updater(*, project_id: str, chapter_index: int, content: str) -> dict[str, Any]:
    return {
        "memory_items_created": 0,
        "foreshadows_planted": 0,
        "foreshadows_resolved": 0,
    }
