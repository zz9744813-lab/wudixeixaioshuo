"""add consolidated_memories table (P5)

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-30 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'consolidated_memories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('scope_type', sa.String(length=50), nullable=True),
        sa.Column('scope_start_chapter', sa.Integer(), nullable=True),
        sa.Column('scope_end_chapter', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('key_events', sa.JSON(), nullable=True),
        sa.Column('character_arcs', sa.JSON(), nullable=True),
        sa.Column('world_updates', sa.JSON(), nullable=True),
        sa.Column('unresolved_hooks', sa.JSON(), nullable=True),
        sa.Column('resolved_hooks', sa.JSON(), nullable=True),
        sa.Column('contradictions', sa.JSON(), nullable=True),
        sa.Column('importance_score', sa.Float(), nullable=True),
        sa.Column('embedding_text', sa.Text(), nullable=True),
        sa.Column('embedding_vector', sa.JSON(), nullable=True),
        sa.Column('embedding_model', sa.String(length=100), nullable=True),
        sa.Column('embedding_updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_consolidated_memories_id'), 'consolidated_memories', ['id'], unique=False)
    op.create_index(op.f('ix_consolidated_memories_project_id'), 'consolidated_memories', ['project_id'], unique=False)
    op.create_index('idx_consolidated_project_scope', 'consolidated_memories',
                    ['project_id', 'scope_start_chapter', 'scope_end_chapter'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_consolidated_project_scope', table_name='consolidated_memories')
    op.drop_index(op.f('ix_consolidated_memories_project_id'), table_name='consolidated_memories')
    op.drop_index(op.f('ix_consolidated_memories_id'), table_name='consolidated_memories')
    op.drop_table('consolidated_memories')
