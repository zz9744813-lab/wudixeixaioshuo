"""
Prompt Template Model - Prompt模板模型
支持版本化、启用/停用、变量插值
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils.time_utils import utc_now


class PromptTemplate(Base):
    """Prompt模板表"""
    __tablename__ = "prompt_templates"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(50), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    version = Column(Integer, default=1)
    content = Column(Text, nullable=False)

    description = Column(Text)
    variables_schema = Column(Text)  # JSON string
    is_active = Column(Integer, default=1)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # 关系
    project = relationship("Project", back_populates="prompt_templates")
