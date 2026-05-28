"""
模型导入集合
"""

from app.models.book import Book, BookChapter
from app.models.chapter import Chapter, ChapterStatus, ChapterVersion
from app.models.evolution import EvolutionLog, EvolutionRun, VersionHistory
from app.models.feedback import Feedback, UserPreference
from app.models.memory import (
    CharacterMemory,
    ChapterMemory,
    WorldMemory,
    RelationshipMemory,
)
from app.models.model_config import ModelCallLog, ModelProvider, ModelRole
from app.models.project import NovelBible, Project
from app.models.task import GenerationStep, GenerationTask
from app.models.technique import (
    BookProfile,
    FailurePattern,
    ProjectPlaybook,
    StoryPattern,
    TechniqueCard,
)
from app.models.foreshadow import (
    Foreshadow,
    ForeshadowPlan,
    ForeshadowReview,
)

__all__ = [
    "Project",
    "NovelBible",
    "Book",
    "BookChapter",
    "Chapter",
    "ChapterStatus",
    "ChapterVersion",
    "GenerationTask",
    "GenerationStep",
    "TechniqueCard",
    "StoryPattern",
    "FailurePattern",
    "ProjectPlaybook",
    "BookProfile",
    # Foreshadow models (P4 Phase 3)
    "Foreshadow",
    "ForeshadowPlan",
    "ForeshadowReview",
    "ModelProvider",
    "ModelRole",
    "ModelCallLog",
    "Feedback",
    "UserPreference",
    "EvolutionRun",
    "EvolutionLog",
    "VersionHistory",
    # Memory models (P4 Phase 1)
    "CharacterMemory",
    "ChapterMemory",
    "WorldMemory",
    "RelationshipMemory",
]
