"""Prompt Registry loader (spec §28).

Prompts live as versioned ``.md`` files (NOT hardcoded in Python, 禁止12) under
``app/prompts/``. Each file has YAML frontmatter:

    ---
    id: scene_event
    version: "1.0"
    purpose: Extract state-changing Events from a Scene
    model_class: structured
    input_schema: {scene_text: str}
    output_schema: {events: [EventItem]}
    change_reason: initial
    ---

    <system prompt body>

:func:`load_prompts` upserts each into the ``prompt_registry`` table (keyed by
``id``), so Agents read versioned prompts from the DB at runtime.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

import yaml
from sqlalchemy.orm import Session

from app.core.ids import new_id
from app.models.infra import PromptRegistry

_PROMPTS_DIR = Path(__file__).resolve().parent

_FRONTMATTER = "---"


def _parse_frontmatter(text: str):
    if not text.startswith(_FRONTMATTER):
        return {}, text
    end = text.find("\n" + _FRONTMATTER, 3)
    if end == -1:
        return {}, text
    fm_text = text[3:end].strip()
    body = text[end + 4 :].lstrip("\n")
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, body


def load_prompts(db: Session, directory: Path | None = None) -> int:
    """Upsert all ``*.md`` prompts into ``prompt_registry``. Returns count."""
    directory = directory or _PROMPTS_DIR
    count = 0
    for path in sorted(directory.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        fm, body = _parse_frontmatter(text)
        pid = fm.get("id") or path.stem
        existing = db.get(PromptRegistry, pid)
        row = existing or PromptRegistry(id=pid)
        row.version = str(fm.get("version", "1.0"))
        row.purpose = fm.get("purpose", path.stem)
        row.input_schema = fm.get("input_schema", {})
        row.output_schema = fm.get("output_schema", {})
        row.model_class = fm.get("model_class")
        row.change_reason = fm.get("change_reason")
        row.status = "active"
        row.file_path = str(path.relative_to(_PROMPTS_DIR.parent.parent))
        row.content = body
        if existing is None:
            db.add(row)
        count += 1
    db.commit()
    return count
