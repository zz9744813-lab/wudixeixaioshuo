from __future__ import annotations

from typing import Any

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.entities import Chapter, Project


def get_export_data(db: Session, project_id: str) -> dict[str, Any]:
    """Collect all project data for export."""
    project = db.get(Project, project_id)
    if not project:
        return {}
    chapters = db.execute(
        select(Chapter)
        .where(Chapter.project_id == project_id)
        .order_by(Chapter.chapter_index)
    ).scalars().all()
    return {
        "project": {
            "id": str(project.id),
            "title": project.title,
            "genre": project.genre,
            "description": project.description,
            "target_total_words": project.target_total_words,
            "target_chapter_words": project.target_chapter_words,
            "daily_word_goal": project.daily_word_goal,
        },
        "chapters": [
            {
                "index": ch.chapter_index,
                "title": ch.title,
                "summary": ch.summary,
                "content": ch.content,
                "word_count": ch.word_count,
                "status": ch.status,
            }
            for ch in chapters
        ],
        "exported_at": str(
            db.execute(select(func.now())).scalar_one()
        ),
    }
