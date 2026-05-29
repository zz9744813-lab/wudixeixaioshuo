"""add_cascade_delete_to_foreign_keys

Revision ID: cf572852293f
Revises: 7d0a239b5be7
Create Date: 2026-05-29 17:19:09.692310

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cf572852293f'
down_revision: Union[str, Sequence[str], None] = '7d0a239b5be7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    BE-002: 添加级联删除到所有外键约束

    注意：SQLite不支持直接修改外键约束。
    对于生产环境升级，需要执行以下步骤：

    1. 备份现有数据
    2. 对于每个需要修改的表：
       a. 创建新表（带ON DELETE CASCADE）
       b. 复制数据
       c. 删除旧表
       d. 重命名新表
    3. 重建索引

    受影响的表：
    - review_results: task_id, chapter_id, version_id
    - final_reviews: task_id, chapter_id, version_id
    - memory_query_logs: project_id, chapter_id
    - feedback: project_id, chapter_id
    - foreshadows: project_id
    - foreshadow_plans: project_id, chapter_id
    - foreshadow_reviews: project_id, chapter_id
    - evolution_runs: project_id
    - evolution_logs: evolution_run_id
    - version_history: project_id
    - book_chapters: book_id
    - technique_cards: book_id
    - failure_patterns: project_id
    - project_playbooks: project_id
    - book_profiles: book_id
    - production_policies: project_id
    - production_logs: project_id, chapter_id, task_id
    - production_stats: project_id
    - prompt_templates: project_id

    对于新部署，级联删除会通过SQLAlchemy模型自动生效。
    """
    # SQLite不支持ALTER TABLE修改外键
    # 如需完整迁移，请参考上方注释步骤
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
