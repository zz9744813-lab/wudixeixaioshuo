"""
Database Configuration
数据库配置 - Alembic 接管迁移，生产环境禁用自动建表
"""

import logging
import os
from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

# 配置日志
logger = logging.getLogger(__name__)

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
        logger.info("[Database] SQLite 外键约束已启用")


def init_db():
    """初始化数据库"""
    # 导入所有模型以确保表被创建 - 使用 models 包的 __init__ 导入
    import app.models

    # 启用 SQLite 外键（只需调用一次）
    _enable_sqlite_foreign_keys()

    env = (settings.APP_ENV or "").lower()

    # 生产环境：完全禁用 create_all，强制使用 Alembic
    if env in {"production", "prod", "staging"}:
        logger.info("[Database] 生产环境：跳过 create_all，请运行: alembic upgrade head")
        # 外键已在上面启用，无需重复调用
        return

    # 开发环境：检查是否启用自动建表
    if settings.APP_AUTO_CREATE_TABLES:
        logger.info("[Database] 开发环境：自动创建表（APP_AUTO_CREATE_TABLES=true）")
        Base.metadata.create_all(bind=engine)
        logger.info(f"[Database] 数据库表已创建: {DATABASE_URL}")
    else:
        logger.info("[Database] 开发环境：跳过 create_all（APP_AUTO_CREATE_TABLES=false）")
        logger.info("[Database] 请运行: alembic upgrade head")

    # P7 调度中心: 幂等列迁移（create_all 不会加已存在表的列）
    _ensure_columns()

    # 初始化默认Prompt模板
    try:
        db = SessionLocal()
        from app.services.default_prompt_templates import (
            seed_default_prompt_templates,
            seed_p6_prompt_templates,
        )
        from app.services.review.reader_setup_service import seed_p6_reader_agents
        seed_default_prompt_templates(db)
        seed_p6_prompt_templates(db)
        seed_p6_reader_agents(db)
        db.close()
    except Exception as e:
        logger.warning(f"[Database] 默认模板初始化失败: {e}")


def _ensure_columns():
    """幂等地为已存在的表添加新列、为缺失的表创建新表。
    适用于开发环境无 alembic 的情况。
    SQLite 用 PRAGMA table_info 反射 schema。

    P7 调度中心:
    - 加列: model_providers / model_roles / model_call_logs
    - 建表: model_routing_events (新表，只能 create_all)
    """
    if "sqlite" not in DATABASE_URL:
        return  # 非 SQLite 暂不处理（生产用 alembic）

    # (表名, [(列名, SQL类型)])
    migrations = [
        ("model_providers", [
            ("status", "VARCHAR(30) DEFAULT 'unknown'"),
            ("avg_latency_ms", "INTEGER"),
        ]),
        ("model_roles", [
            ("assignment_mode", "VARCHAR(20) DEFAULT 'auto'"),
            ("allowed_provider_ids", "TEXT"),
            ("preferred_quality", "VARCHAR(30) DEFAULT 'balanced'"),
            ("max_cost_per_million", "FLOAT"),
            ("min_context_tokens", "INTEGER"),
            ("require_json", "INTEGER DEFAULT 0"),
            ("require_streaming", "INTEGER DEFAULT 0"),
            ("fallback_enabled", "INTEGER DEFAULT 1"),
            ("updated_by", "VARCHAR(50) DEFAULT 'system'"),
        ]),
        ("model_call_logs", [
            ("routing_event_id", "INTEGER"),
        ]),
        # P6: 给 GenerationTask 加 payload JSON 列 (Worker 多任务调度需要存 task 参数)
        ("generation_tasks", [
            ("payload", "TEXT"),
        ]),
    ]

    with engine.begin() as conn:
        for table_name, columns in migrations:
            try:
                result = conn.execute(text(f"PRAGMA table_info({table_name})"))
                existing = {row[1] for row in result.fetchall()}
            except Exception as e:
                logger.debug(f"[Database] PRAGMA table_info({table_name}) 失败: {e}")
                continue

            for col_name, col_type in columns:
                if col_name in existing:
                    continue
                try:
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}"))
                    logger.info(f"[Database] 已添加列 {table_name}.{col_name} {col_type}")
                except Exception as e:
                    logger.warning(f"[Database] 添加列 {table_name}.{col_name} 失败: {e}")

    # 新表只能 create_all（_ensure_columns 不适合处理新建表的主键/外键等）
    # SQLAlchemy create_all 幂等，已存在的表不会重建
    try:
        Base.metadata.create_all(bind=engine, tables=[
            t for t in Base.metadata.tables.values()
            if t.name in ("model_routing_events", "reader_agent_profiles",
                          "review_comments", "review_comment_groups",
                          "reader_review_runs", "review_settings")
        ])
        logger.info("[Database] 已检查 P7/P6 新表")
    except Exception as e:
        logger.warning(f"[Database] 创建新表失败: {e}")
