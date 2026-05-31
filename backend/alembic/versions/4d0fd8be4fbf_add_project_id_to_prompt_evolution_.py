"""add project_id to prompt evolution policies

Revision ID: 4d0fd8be4fbf
Revises: 4ac89cf917f0
Create Date: 2026-05-31
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '4d0fd8be4fbf'
down_revision: Union[str, Sequence[str], None] = '4ac89cf917f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("prompt_evolution_policies") as batch_op:
        batch_op.add_column(sa.Column("project_id", sa.Integer(), nullable=True))
        batch_op.create_index(
            "ix_prompt_evolution_policies_project_id",
            ["project_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("prompt_evolution_policies") as batch_op:
        batch_op.drop_index("ix_prompt_evolution_policies_project_id")
        batch_op.drop_column("project_id")
