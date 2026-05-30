"""add_reader_training_to_automation_policy

Revision ID: 4ac89cf917f0
Revises: b8c9d0e1f2a3
Create Date: 2026-05-31 01:00:06.288241

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4ac89cf917f0'
down_revision: Union[str, Sequence[str], None] = 'b8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "automation_policies",
        sa.Column("enable_reader_training", sa.Integer(), nullable=True, server_default="1"),
    )
    op.add_column(
        "automation_policies",
        sa.Column("reader_training_min_batch", sa.Integer(), nullable=True, server_default="5"),
    )
    op.add_column(
        "automation_policies",
        sa.Column("reader_training_interval_minutes", sa.Integer(), nullable=True, server_default="30"),
    )
    op.add_column(
        "automation_policies",
        sa.Column("last_reader_training_batch_id", sa.Integer(), nullable=True, server_default="0"),
    )
    op.add_column(
        "automation_policies",
        sa.Column("last_reader_training_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("automation_policies", "last_reader_training_at")
    op.drop_column("automation_policies", "last_reader_training_batch_id")
    op.drop_column("automation_policies", "reader_training_interval_minutes")
    op.drop_column("automation_policies", "reader_training_min_batch")
    op.drop_column("automation_policies", "enable_reader_training")
