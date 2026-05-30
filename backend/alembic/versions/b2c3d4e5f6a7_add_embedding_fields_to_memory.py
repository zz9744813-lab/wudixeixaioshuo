"""add embedding fields to memory tables (P4)

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-30 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = [
    "chapter_memories",
    "character_memories",
    "world_memories",
    "relationship_memories",
]


def upgrade() -> None:
    """Upgrade schema."""
    for table in _TABLES:
        op.add_column(table, sa.Column('embedding_text', sa.Text(), nullable=True))
        op.add_column(table, sa.Column('embedding_vector', sa.JSON(), nullable=True))
        op.add_column(table, sa.Column('embedding_model', sa.String(length=100), nullable=True))
        op.add_column(table, sa.Column('embedding_updated_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    for table in _TABLES:
        op.drop_column(table, 'embedding_updated_at')
        op.drop_column(table, 'embedding_model')
        op.drop_column(table, 'embedding_vector')
        op.drop_column(table, 'embedding_text')
