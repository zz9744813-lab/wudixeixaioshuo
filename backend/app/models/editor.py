"""
总编与书级状态模型 (P2)
- EditorDirective: 章级全局写作指令
- BookState: 全书状态快照
"""

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String, Text

from app.database import Base
from app.utils.time_utils import utc_now


class EditorDirective(Base):
    """总编对单章的全局写作指令（同一 chapter_id 只保留最新一条）"""
    __tablename__ = "editor_directives"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, index=True, nullable=False)
    chapter_id = Column(Integer, index=True, nullable=False)
    chapter_index = Column(Integer, index=True, nullable=False)

    directive = Column(JSON, default=dict)
    formatted_prompt = Column(Text, nullable=True)

    source = Column(String(50), default="chief_editor")
    model_name = Column(String(200), nullable=True)
    provider_name = Column(String(100), nullable=True)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cost = Column(Float, default=0.0)

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class BookState(Base):
    """全书状态快照（每个项目唯一）"""
    __tablename__ = "book_states"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, unique=True, index=True)

    current_volume = Column(String(100), nullable=True)
    current_arc = Column(String(100), nullable=True)
    current_stage = Column(String(100), nullable=True)

    tension_curve = Column(JSON, default=list)
    active_plotlines = Column(JSON, default=list)
    active_foreshadows = Column(JSON, default=list)
    character_arcs = Column(JSON, default=dict)
    unresolved_conflicts = Column(JSON, default=list)
    next_payoff_candidates = Column(JSON, default=list)

    last_analyzed_chapter_index = Column(Integer, default=0)
    summary = Column(Text, nullable=True)

    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    created_at = Column(DateTime, default=utc_now)
