"""Model package. Importing this module registers every table on
``app.db.Base.metadata`` so Alembic autogenerate and ``create_all`` see them.
"""
from __future__ import annotations

from app.db import Base

# Import submodules for their side-effect of registering mapped classes.
from app.models import (  # noqa: E402,F401
    enums,
    _mixin,
    corpus,
    decomposition,
    character,
    knowledge,
    relationship,
    emotion,
    conflict,
    technique,
    research,
    evaluation,
    knowledge_registry,
    infra,
    research_graph,
    benchmark,
    user_feedback,
    claims,
)

__all__ = ["Base"]
