"""
Database Configuration
数据库配置
"""

import os
from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, event
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
        task,
        technique,
    )

    Base.metadata.create_all(bind=engine)
    print(f"[Database] 数据库已初始化: {DATABASE_URL}")
