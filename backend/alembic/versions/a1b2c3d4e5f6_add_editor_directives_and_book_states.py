"""add editor_directives and book_states (P2)

Revision ID: a1b2c3d4e5f6
Revises: 60282021bafa
Create Date: 2026-05-30 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '60282021bafa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'editor_directives',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('chapter_id', sa.Integer(), nullable=False),
        sa.Column('chapter_index', sa.Integer(), nullable=False),
        sa.Column('directive', sa.JSON(), nullable=True),
        sa.Column('formatted_prompt', sa.Text(), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=True),
        sa.Column('model_name', sa.String(length=200), nullable=True),
        sa.Column('provider_name', sa.String(length=100), nullable=True),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('cost', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_editor_directives_id'), 'editor_directives', ['id'], unique=False)
    op.create_index(op.f('ix_editor_directives_project_id'), 'editor_directives', ['project_id'], unique=False)
    op.create_index(op.f('ix_editor_directives_chapter_id'), 'editor_directives', ['chapter_id'], unique=False)
    op.create_index(op.f('ix_editor_directives_chapter_index'), 'editor_directives', ['chapter_index'], unique=False)

    op.create_table(
        'book_states',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('current_volume', sa.String(length=100), nullable=True),
        sa.Column('current_arc', sa.String(length=100), nullable=True),
        sa.Column('current_stage', sa.String(length=100), nullable=True),
        sa.Column('tension_curve', sa.JSON(), nullable=True),
        sa.Column('active_plotlines', sa.JSON(), nullable=True),
        sa.Column('active_foreshadows', sa.JSON(), nullable=True),
        sa.Column('character_arcs', sa.JSON(), nullable=True),
        sa.Column('unresolved_conflicts', sa.JSON(), nullable=True),
        sa.Column('next_payoff_candidates', sa.JSON(), nullable=True),
        sa.Column('last_analyzed_chapter_index', sa.Integer(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_book_states_id'), 'book_states', ['id'], unique=False)
    op.create_index(op.f('ix_book_states_project_id'), 'book_states', ['project_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_book_states_project_id'), table_name='book_states')
    op.drop_index(op.f('ix_book_states_id'), table_name='book_states')
    op.drop_table('book_states')
    op.drop_index(op.f('ix_editor_directives_chapter_index'), table_name='editor_directives')
    op.drop_index(op.f('ix_editor_directives_chapter_id'), table_name='editor_directives')
    op.drop_index(op.f('ix_editor_directives_project_id'), table_name='editor_directives')
    op.drop_index(op.f('ix_editor_directives_id'), table_name='editor_directives')
    op.drop_table('editor_directives')
