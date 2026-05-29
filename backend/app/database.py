"""
Database Configuration
数据库配置 - Alembic 接管迁移，生产环境禁用自动建表
"""

import os
from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

# 数据库配置 - 从配置中心读取
DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "novel_agent.db")
DATABASE_URL = settings.DATABASE_URL or f"sqlite:///{DEFAULT_DB_PATH}"

# 创建引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False,
)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 模型基类
Base = declarative_base()


def get_db():
    """获取数据库会话（依赖注入用）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _enable_sqlite_foreign_keys():
    """SQLite 启用外键约束"""
    if "sqlite" in DATABASE_URL:
        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        print("[Database] SQLite 外键约束已启用")


def _ensure_model_call_log_columns():
    """
    [已废弃] 确保 model_call_logs 表有所有必需的列
    已由 Alembic 迁移接管，此函数将在未来版本移除
    """
    # 生产环境完全禁用自动迁移
    env = (settings.APP_ENV or "").lower()
    if env in {"production", "prod", "staging"}:
        print("[Database] 生产环境：跳过自动迁移检查，请使用 alembic upgrade head")
        return

    # 非生产环境且启用自动建表时才检查
    if not settings.APP_AUTO_CREATE_TABLES:
        return

    if "sqlite" not in DATABASE_URL:
        return  # 仅SQLite支持PRAGMA

    try:
        with engine.connect() as conn:
            # 检查 model_call_logs 表是否存在
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='model_call_logs'"
            ))
            if not result.fetchone():
                return  # 表不存在，让create_all创建

            # 获取现有列
            columns = conn.execute(text("PRAGMA table_info(model_call_logs)"))
            column_names = {row[1] for row in columns}

            # 检查并添加 project_id 列
            if 'project_id' not in column_names:
                print("[Database] 检测到缺少 project_id 列，正在添加...")
                conn.execute(text(
                    "ALTER TABLE model_call_logs ADD COLUMN project_id INTEGER REFERENCES projects(id)"
                ))
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS ix_model_call_logs_project_id ON model_call_logs(project_id)"
                ))
                conn.commit()
                print("[Database] project_id 列添加完成")

    except Exception as e:
        print(f"[Database] 自动迁移检查失败: {e}")


def init_db():
    """初始化数据库"""
    # 导入所有模型以确保表被创建
    from app.models import (
        book,
        chapter,
        evolution,
        feedback,
        model_config,
        project,
        prompt_template,
        task,
        technique,
    )

    # 启用 SQLite 外键
    _enable_sqlite_foreign_keys()

    env = (settings.APP_ENV or "").lower()

    # 生产环境：完全禁用 create_all，强制使用 Alembic
    if env in {"production", "prod", "staging"}:
        print("[Database] 生产环境：跳过 create_all，请运行: alembic upgrade head")
        # 仅启用外键，不做任何 schema 变更
        _enable_sqlite_foreign_keys()
        return

    # 开发环境：检查是否启用自动建表
    if settings.APP_AUTO_CREATE_TABLES:
        print("[Database] 开发环境：自动创建表（APP_AUTO_CREATE_TABLES=true）")
        # 自动迁移：确保老数据库有所有列
        _ensure_model_call_log_columns()
        Base.metadata.create_all(bind=engine)
        print(f"[Database] 数据库表已创建: {DATABASE_URL}")
    else:
        print("[Database] 开发环境：跳过 create_all（APP_AUTO_CREATE_TABLES=false）")
        print("[Database] 请运行: alembic upgrade head")

    # 初始化默认Prompt模板
    try:
        db = SessionLocal()
        from app.services.default_prompt_templates import seed_default_prompt_templates
        seed_default_prompt_templates(db)
        db.close()
    except Exception as e:
        print(f"[Database] 默认模板初始化失败: {e}")
