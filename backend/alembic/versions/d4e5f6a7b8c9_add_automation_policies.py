"""add automation_policies table (P8)

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-30 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'automation_policies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('enable_editor_review', sa.Integer(), nullable=True),
        sa.Column('editor_review_every_n_chapters', sa.Integer(), nullable=True),
        sa.Column('enable_research', sa.Integer(), nullable=True),
        sa.Column('research_interval_hours', sa.Integer(), nullable=True),
        sa.Column('enable_evolution', sa.Integer(), nullable=True),
        sa.Column('evolution_check_every_n_chapters', sa.Integer(), nullable=True),
        sa.Column('min_samples_for_evolution', sa.Integer(), nullable=True),
        sa.Column('enable_parallel_draft', sa.Integer(), nullable=True),
        sa.Column('parallel_draft_candidates', sa.Integer(), nullable=True),
        sa.Column('parallel_draft_max_concurrency', sa.Integer(), nullable=True),
        sa.Column('max_auto_cost_per_day', sa.Float(), nullable=True),
        sa.Column('last_editor_review_chapter', sa.Integer(), nullable=True),
        sa.Column('last_evolution_chapter', sa.Integer(), nullable=True),
        sa.Column('last_research_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_automation_policies_id'), 'automation_policies', ['id'], unique=False)
    op.create_index(op.f('ix_automation_policies_project_id'), 'automation_policies', ['project_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_automation_policies_project_id'), table_name='automation_policies')
    op.drop_index(op.f('ix_automation_policies_id'), table_name='automation_policies')
    op.drop_table('automation_policies')
