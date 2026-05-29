"""
Book Analysis Models - 书籍分析模型 (B3)
结构指纹 / 爽点曲线数据存储
"""

from datetime import datetime
from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils.time_utils import utc_now


class BookAnalysisProfile(Base):
    """
    书籍分析档案 - 存储对参考书籍的结构分析结果
    包含结构指纹、爽点曲线、节奏模式等
    """
    __tablename__ = "book_analysis_profiles"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(
        Integer,
        ForeignKey("books.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 基础统计
    total_chapters = Column(Integer, default=0)  # 总章节数
    total_words = Column(Integer, default=0)  # 总字数
    avg_chapter_words = Column(Float, default=3000.0)  # 平均章节字数
    chapter_word_std = Column(Float, default=500.0)  # 章节字数标准差

    # Hook/断章分析
    hook_rate = Column(Float, default=0.7)  # 带Hook的章节比例
    cliffhanger_rate = Column(Float, default=0.3)  # 断章比例

    # 爽点曲线 (Satisfaction Curve)
    payoff_cadence_chapters = Column(Float, default=5.0)  # 爽点间隔（章节数）
    emotion_curve = Column(JSON, default=dict)  # 情绪曲线模式
    # 示例: {
    #     "baseline": 5.0,           # 基线情绪强度
    #     "peak_intensity": 9.0,     # 峰值强度
    #     "valley_depth": 3.0,       # 低谷深度
    #     "rhythm": "wave",          # 节奏类型: wave/intense/calm
    # }

    # 节奏规则
    pacing_rules = Column(JSON, default=dict)  # 节奏规则
    # 示例: {
    #     "opening_pace": "medium",      # 开局节奏: slow/medium/fast
    #     "rising_action_ratio": 0.4,    # 上升动作占比
    #     "climax_density": "high",      # 高潮密度
    #     "resolution_brevity": "concise", # 收尾简洁度
    # }

    # 人物弧线模式
    character_arc_patterns = Column(JSON, default=list)  # 人物成长弧线模板

    # 情节结构
    plot_structure = Column(JSON, default=dict)  # 情节结构分析
    # 示例: {
    #     "act_structure": "three_act",  # 幕结构
    #     "turning_points_per_volume": 3, # 每卷转折点数
    # }

    # 爽点峰值位置
    satisfaction_peaks = Column(JSON, default=list)  # 爽点章节索引列表
    # 示例: [{"chapter_index": 5, "intensity": 9.5, "type": "breakthrough"}, ...]

    # 元数据
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # 关系
    book = relationship("Book", back_populates="analysis_profiles")
    applied_projects = relationship(
        "ProjectStyleProfile",
        back_populates="book_analysis",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "book_id": self.book_id,
            "total_chapters": self.total_chapters,
            "total_words": self.total_words,
            "avg_chapter_words": self.avg_chapter_words,
            "chapter_word_std": self.chapter_word_std,
            "hook_rate": self.hook_rate,
            "cliffhanger_rate": self.cliffhanger_rate,
            "payoff_cadence_chapters": self.payoff_cadence_chapters,
            "emotion_curve": self.emotion_curve,
            "pacing_rules": self.pacing_rules,
            "character_arc_patterns": self.character_arc_patterns,
            "plot_structure": self.plot_structure,
            "satisfaction_peaks": self.satisfaction_peaks,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ProjectStyleProfile(Base):
    """
    项目风格档案 - 将书籍分析应用到具体写作项目
    存储派生的写作规则和约束
    """
    __tablename__ = "project_style_profiles"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    profile_name = Column(String(200), nullable=False)  # 档案名称

    # 关联的书籍分析
    book_analysis_id = Column(
        Integer,
        ForeignKey("book_analysis_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # 派生的写作规则
    derived_rules = Column(JSON, default=dict)  # 派生规则
    # 示例: {
    #     "target_chapter_words": {"min": 2500, "optimal": 3000, "max": 3500},
    #     "hook_requirements": {"opening_hook": true, "hook_intensity": "strong"},
    #     "cliffhanger_frequency": 0.3,
    #     "satisfaction_cadence": 5.0,
    #     "emotion_guidelines": {...},
    #     "pacing_template": {...},
    # }

    # 状态
    enabled = Column(Boolean, default=True)  # 是否启用

    # 元数据
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # 关系
    project = relationship("Project", back_populates="style_profiles")
    book_analysis = relationship("BookAnalysisProfile", back_populates="applied_projects")

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "profile_name": self.profile_name,
            "book_analysis_id": self.book_analysis_id,
            "derived_rules": self.derived_rules,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def get_active_rules(self) -> dict:
        """获取启用的规则（过滤掉禁用的）"""
        if not self.enabled:
            return {}
        return self.derived_rules or {}
