"""add daily_usage_stats and prompt_ab_test_runs (fix missing tables)

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-05-30 18:30:00.000000

补建两张"有模型、squash 时遗漏建表"的表：
- daily_usage_stats: worker 预算闸门热路径依赖，缺表会导致每次取任务即崩
- prompt_ab_test_runs: P6 真实 A/B 落库依赖，缺表会导致进化一跑就崩
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if 'daily_usage_stats' not in existing:
        op.create_table(
            'daily_usage_stats',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('date', sa.Date(), nullable=False),
            sa.Column('project_id', sa.Integer(), nullable=True),
            sa.Column('provider', sa.String(length=100), nullable=True),
            sa.Column('model_name', sa.String(length=200), nullable=True),
            sa.Column('input_tokens', sa.Integer(), nullable=True),
            sa.Column('output_tokens', sa.Integer(), nullable=True),
            sa.Column('total_tokens', sa.Integer(), nullable=True),
            sa.Column('cost', sa.Float(), nullable=True),
            sa.Column('chapter_count', sa.Integer(), nullable=True),
            sa.Column('task_count', sa.Integer(), nullable=True),
            sa.Column('success_count', sa.Integer(), nullable=True),
            sa.Column('failure_count', sa.Integer(), nullable=True),
            sa.Column('word_count', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.Date(), nullable=True),
            sa.Column('updated_at', sa.Date(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('date', 'project_id', 'provider', 'model_name',
                                name='uix_daily_stats'),
        )
        op.create_index(op.f('ix_daily_usage_stats_id'), 'daily_usage_stats', ['id'], unique=False)
        op.create_index(op.f('ix_daily_usage_stats_date'), 'daily_usage_stats', ['date'], unique=False)
        op.create_index(op.f('ix_daily_usage_stats_project_id'), 'daily_usage_stats', ['project_id'], unique=False)

    if 'prompt_ab_test_runs' not in existing:
        op.create_table(
            'prompt_ab_test_runs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('project_id', sa.Integer(), nullable=True),
            sa.Column('role', sa.String(length=50), nullable=True),
            sa.Column('baseline_prompt_id', sa.Integer(), nullable=True),
            sa.Column('candidate_prompt_id', sa.Integer(), nullable=True),
            sa.Column('sample_ids', sa.JSON(), nullable=True),
            sa.Column('baseline_avg_score', sa.Float(), nullable=True),
            sa.Column('candidate_avg_score', sa.Float(), nullable=True),
            sa.Column('improvement', sa.Float(), nullable=True),
            sa.Column('passed', sa.Integer(), nullable=True),
            sa.Column('decision', sa.String(length=50), nullable=True),
            sa.Column('details', sa.JSON(), nullable=True),
            sa.Column('total_cost', sa.Float(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_prompt_ab_test_runs_id'), 'prompt_ab_test_runs', ['id'], unique=False)
        op.create_index(op.f('ix_prompt_ab_test_runs_project_id'), 'prompt_ab_test_runs', ['project_id'], unique=False)
        op.create_index(op.f('ix_prompt_ab_test_runs_role'), 'prompt_ab_test_runs', ['role'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_prompt_ab_test_runs_role'), table_name='prompt_ab_test_runs')
    op.drop_index(op.f('ix_prompt_ab_test_runs_project_id'), table_name='prompt_ab_test_runs')
    op.drop_index(op.f('ix_prompt_ab_test_runs_id'), table_name='prompt_ab_test_runs')
    op.drop_table('prompt_ab_test_runs')
    op.drop_index(op.f('ix_daily_usage_stats_project_id'), table_name='daily_usage_stats')
    op.drop_index(op.f('ix_daily_usage_stats_date'), table_name='daily_usage_stats')
    op.drop_index(op.f('ix_daily_usage_stats_id'), table_name='daily_usage_stats')
    op.drop_table('daily_usage_stats')
