"""
自动化策略模型 (P8)
"""

from sqlalchemy import Column, DateTime, Float, Integer

from app.database import Base
from app.utils.time_utils import utc_now


class AutomationPolicy(Base):
    """项目级自动化策略"""
    __tablename__ = "automation_policies"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, index=True, nullable=False)

    enable_editor_review = Column(Integer, default=1)
    editor_review_every_n_chapters = Column(Integer, default=5)

    enable_research = Column(Integer, default=0)
    research_interval_hours = Column(Integer, default=24)

    enable_evolution = Column(Integer, default=1)
    evolution_check_every_n_chapters = Column(Integer, default=5)
    min_samples_for_evolution = Column(Integer, default=3)

    enable_parallel_draft = Column(Integer, default=0)
    parallel_draft_candidates = Column(Integer, default=3)
    parallel_draft_max_concurrency = Column(Integer, default=3)

    max_auto_cost_per_day = Column(Float, default=5.0)

    last_editor_review_chapter = Column(Integer, default=0)
    last_evolution_chapter = Column(Integer, default=0)
    last_research_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
