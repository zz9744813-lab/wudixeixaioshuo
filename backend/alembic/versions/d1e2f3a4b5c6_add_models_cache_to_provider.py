"""add_models_cache_to_provider

Revision ID: d1e2f3a4b5c6
Revises: 4d0fd8be4fbf
Create Date: 2026-05-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = '4d0fd8be4fbf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite: 使用 batch_alter_table 避免 ALTER 约束问题
    with op.batch_alter_table('model_providers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('models_cache', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('last_models_refresh', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('discovery_status', sa.String(50), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('model_providers', schema=None) as batch_op:
        batch_op.drop_column('discovery_status')
        batch_op.drop_column('last_models_refresh')
        batch_op.drop_column('models_cache')
