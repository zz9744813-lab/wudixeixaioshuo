"""add_cascade_delete_to_foreign_keys

Revision ID: cf572852293f
Revises: 7d0a239b5be7
Create Date: 2026-05-29 17:19:09.692310

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'cf572852293f'
down_revision: Union[str, Sequence[str], None] = '7d0a239b5be7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema: 添加级联删除到关键外键约束

    BE-002 要求的两处级联：
    1. novel_bibles.project_id -> projects.id ON DELETE CASCADE
    2. book_chapters.book_id -> books.id ON DELETE CASCADE

    SQLite 不支持 ALTER TABLE 修改外键，使用临时表重建方案。
    """
    conn = op.get_bind()
    inspector = inspect(conn)

    # ========== 1. 处理 novel_bibles 表 ==========
    if 'novel_bibles' in inspector.get_table_names():
        _recreate_novel_bibles_with_cascade()

    # ========== 2. 处理 book_chapters 表 ==========
    if 'book_chapters' in inspector.get_table_names():
        _recreate_book_chapters_with_cascade()


def _recreate_novel_bibles_with_cascade():
    """重建 novel_bibles 表，添加 ON DELETE CASCADE"""
    # 获取现有数据
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT * FROM novel_bibles"))
    rows = result.fetchall()

    # 创建新表（带 CASCADE）
    op.create_table(
        'novel_bibles_new',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('world_setting', sa.Text(), nullable=True),
        sa.Column('world_rules', sa.JSON(), nullable=True),
        sa.Column('timeline', sa.JSON(), nullable=True),
        sa.Column('characters', sa.JSON(), nullable=True),
        sa.Column('character_relationships', sa.JSON(), nullable=True),
        sa.Column('main_plot', sa.Text(), nullable=True),
        sa.Column('sub_plots', sa.JSON(), nullable=True),
        sa.Column('foreshadowing', sa.JSON(), nullable=True),
        sa.Column('style_boundaries', sa.JSON(), nullable=True),
        sa.Column('tone_guidelines', sa.Text(), nullable=True),
        sa.Column('forbidden_items', sa.JSON(), nullable=True),
        sa.Column('volume_outline', sa.JSON(), nullable=True),
        sa.Column('chapter_outline', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id')
    )

    # 复制数据
    if rows:
        columns = [
            'id', 'project_id', 'world_setting', 'world_rules', 'timeline',
            'characters', 'character_relationships', 'main_plot', 'sub_plots',
            'foreshadowing', 'style_boundaries', 'tone_guidelines', 'forbidden_items',
            'volume_outline', 'chapter_outline', 'created_at', 'updated_at'
        ]
        for row in rows:
            data = {col: getattr(row, col, None) for col in columns}
            op.execute(
                sa.text("""
                    INSERT INTO novel_bibles_new (id, project_id, world_setting, world_rules, timeline,
                        characters, character_relationships, main_plot, sub_plots, foreshadowing,
                        style_boundaries, tone_guidelines, forbidden_items, volume_outline,
                        chapter_outline, created_at, updated_at)
                    VALUES (:id, :project_id, :world_setting, :world_rules, :timeline,
                        :characters, :character_relationships, :main_plot, :sub_plots, :foreshadowing,
                        :style_boundaries, :tone_guidelines, :forbidden_items, :volume_outline,
                        :chapter_outline, :created_at, :updated_at)
                """),
                data
            )

    # 删除旧表，重命名新表
    op.drop_table('novel_bibles')
    op.rename_table('novel_bibles_new', 'novel_bibles')

    # 重建索引
    op.create_index('ix_novel_bibles_id', 'novel_bibles', ['id'], unique=False)


def _recreate_book_chapters_with_cascade():
    """重建 book_chapters 表，添加 ON DELETE CASCADE"""
    # 获取现有数据
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT * FROM book_chapters"))
    rows = result.fetchall()

    # 创建新表（带 CASCADE）
    op.create_table(
        'book_chapters_new',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('book_id', sa.Integer(), nullable=False),
        sa.Column('chapter_index', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=300), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('word_count', sa.Integer(), nullable=True),
        sa.Column('structure_analysis', sa.JSON(), nullable=True),
        sa.Column('character_mentions', sa.JSON(), nullable=True),
        sa.Column('plot_points', sa.JSON(), nullable=True),
        sa.Column('emotional_beats', sa.JSON(), nullable=True),
        sa.Column('hooks', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 复制数据
    if rows:
        for row in rows:
            data = {
                'id': row.id,
                'book_id': row.book_id,
                'chapter_index': row.chapter_index,
                'title': getattr(row, 'title', None),
                'content': getattr(row, 'content', None),
                'summary': getattr(row, 'summary', None),
                'word_count': getattr(row, 'word_count', 0),
                'structure_analysis': getattr(row, 'structure_analysis', None),
                'character_mentions': getattr(row, 'character_mentions', None),
                'plot_points': getattr(row, 'plot_points', None),
                'emotional_beats': getattr(row, 'emotional_beats', None),
                'hooks': getattr(row, 'hooks', None),
                'created_at': getattr(row, 'created_at', None),
            }
            op.execute(
                sa.text("""
                    INSERT INTO book_chapters_new (id, book_id, chapter_index, title, content, summary,
                        word_count, structure_analysis, character_mentions, plot_points,
                        emotional_beats, hooks, created_at)
                    VALUES (:id, :book_id, :chapter_index, :title, :content, :summary,
                        :word_count, :structure_analysis, :character_mentions, :plot_points,
                        :emotional_beats, :hooks, :created_at)
                """),
                data
            )

    # 删除旧表，重命名新表
    op.drop_table('book_chapters')
    op.rename_table('book_chapters_new', 'book_chapters')

    # 重建索引
    op.create_index('ix_book_chapters_id', 'book_chapters', ['id'], unique=False)


def downgrade() -> None:
    """
    Downgrade schema: 移除级联删除

    注意：downgrade 会丢失 ON DELETE CASCADE 行为，但不会删除数据。
    """
    # Downgrade 操作较为复杂，涉及再次重建表
    # 在生产环境中，通常不建议降级外键约束
    # 如需完整降级，需要再次重建表（不带 CASCADE）
    pass
