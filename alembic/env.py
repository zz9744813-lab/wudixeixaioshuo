"""Alembic environment. Uses the application's settings for the DB URL and
the application's declarative ``Base.metadata`` as the autogenerate target.
"""
from __future__ import annotations

import sys
from logging.config import fileConfig

from alembic import context

# Make `app` importable when alembic runs from the repo root.
sys.path.insert(0, ".")

from app.config import get_settings  # noqa: E402
from app.db import Base, get_engine  # noqa: E402
from app import models  # noqa: E402,F401  (register all tables)

settings = get_settings()
config = context.config

try:
    if config.config_file_name:
        fileConfig(config.config_file_name)
except Exception:  # pragma: no cover
    pass

config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata


def _configure(**kw):
    return dict(
        target_metadata=target_metadata,
        render_as_batch=True,      # batch mode for SQLite ALTER support
        compare_type=True,
        **kw,
    )


def run_migrations_offline() -> None:
    context.configure(url=settings.database_url, **_configure())
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = get_engine()
    with connectable.connect() as connection:
        context.configure(connection=connection, **_configure())
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
