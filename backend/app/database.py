"""
Database Configuration
数据库配置
"""

import os
from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

# 数据库配置
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///F:/kelaode/quanzidong/data/novel_agent.db"
)

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
