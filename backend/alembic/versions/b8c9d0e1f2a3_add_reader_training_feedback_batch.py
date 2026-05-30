"""add reader training feedback batch (P1)

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-05-30 19:10:00.000000

- 新增 feedback_batches 表
- feedback 表新增异步真人训练营字段
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, Sequence[str], None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_FEEDBACK_COLS = [
    ("reader_score", sa.Float()),
    ("dimension_scores", sa.JSON()),
    ("anchor", sa.JSON()),
    ("reaction", sa.String(length=50)),
    ("applied_from_chapter", sa.Integer()),
    ("batch_id", sa.Integer()),
    ("status", sa.String(length=50)),
]


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "feedback_batches" not in tables:
        op.create_table(
            "feedback_batches",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("chapter_id", sa.Integer(), nullable=True),
            sa.Column("feedback_ids", sa.JSON(), nullable=True),
            sa.Column("feedback_count", sa.Integer(), nullable=True),
            sa.Column("avg_reader_score", sa.Float(), nullable=True),
            sa.Column("avg_system_score", sa.Float(), nullable=True),
            sa.Column("critic_gap", sa.Float(), nullable=True),
            sa.Column("derived_rules", sa.JSON(), nullable=True),
            sa.Column("dimension_summary", sa.JSON(), nullable=True),
            sa.Column("reaction_summary", sa.JSON(), nullable=True),
            sa.Column("triggered_evolution", sa.Integer(), nullable=True),
            sa.Column("triggered_critic_calibration", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(length=50), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("processed_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_feedback_batches_id"), "feedback_batches", ["id"], unique=False)
        op.create_index(op.f("ix_feedback_batches_project_id"), "feedback_batches", ["project_id"], unique=False)
        op.create_index(op.f("ix_feedback_batches_chapter_id"), "feedback_batches", ["chapter_id"], unique=False)

    existing_cols = {c["name"] for c in inspector.get_columns("feedback")}
    for name, col_type in _FEEDBACK_COLS:
        if name not in existing_cols:
            op.add_column("feedback", sa.Column(name, col_type, nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    for name, _ in reversed(_FEEDBACK_COLS):
        op.drop_column("feedback", name)
    op.drop_index(op.f("ix_feedback_batches_chapter_id"), table_name="feedback_batches")
    op.drop_index(op.f("ix_feedback_batches_project_id"), table_name="feedback_batches")
    op.drop_index(op.f("ix_feedback_batches_id"), table_name="feedback_batches")
    op.drop_table("feedback_batches")
