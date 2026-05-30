"""add meta and updated_at to chapter_memories (fix B4 missing fields)

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-05-30 18:50:00.000000

ChapterMemory 模型/服务使用了 meta 与 updated_at，但 schema 缺这两列，
update_chapter_ending_info() 调用时会 AttributeError / 不落库。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("chapter_memories")}
    if "meta" not in cols:
        op.add_column("chapter_memories", sa.Column("meta", sa.JSON(), nullable=True))
    if "updated_at" not in cols:
        op.add_column("chapter_memories", sa.Column("updated_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("chapter_memories", "updated_at")
    op.drop_column("chapter_memories", "meta")
