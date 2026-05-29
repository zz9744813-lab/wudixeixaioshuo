"""
Database Configuration
数据库配置
"""

import os
from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base, sessionmaker

# 数据库配置 - 使用相对路径，支持环境变量覆盖
import os

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "novel_agent.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")

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


def _ensure_model_call_log_columns():
    """
    确保 model_call_logs 表有所有必需的列
    用于已有数据库的自动迁移
    """
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
    """初始化数据库，创建所有表"""
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

    # 自动迁移：确保老数据库有所有列
    _ensure_model_call_log_columns()

    Base.metadata.create_all(bind=engine)
    print(f"[Database] 数据库已初始化: {DATABASE_URL}")

    # 初始化默认Prompt模板
    try:
        db = SessionLocal()
        from app.services.default_prompt_templates import seed_default_prompt_templates
        seed_default_prompt_templates(db)
        db.close()
    except Exception as e:
        print(f"[Database] 默认模板初始化失败: {e}")
