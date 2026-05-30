"""
模型导入集合
"""

from app.models.book import Book, BookChapter
from app.models.book_analysis import BookAnalysisProfile, ProjectStyleProfile
from app.models.chapter import Chapter, ChapterStatus, ChapterVersion
from app.models.consistency import (
    ConsistencyRule,
    ConsistencyCheckResult,
    ConsistencyIssue,
    ConsistencyCheckType,
    ConsistencyIssueSeverity,
    CharacterConsistencyLog,
    TimelineEvent,
)
from app.models.evolution import EvolutionLog, EvolutionRun, VersionHistory
from app.models.feedback import Feedback, UserPreference
from app.models.memory import (
    CharacterMemory,
    ChapterMemory,
    WorldMemory,
    RelationshipMemory,
    ConsolidatedMemory,
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
from app.models.production import (
    ProductionLog,
    ProductionPolicy,
    ProductionStats,
)
from app.models.prompt_template import PromptTemplate
from app.models.review import (
    FinalReview,
    ReviewProfile,
    ReviewResult,
)
from app.models.agent_run import (
    AgentRun,
    AgentRunStatus,
    AgentRunMode,
    AgentPlan,
    AgentPlanStatus,
    AgentStep,
    AgentStepStatus,
    SubAgentTask,
    SubAgentTaskStatus,
)
from app.models.subagent_result import SubAgentResult, SubAgentResultStatus
from app.models.provider_route_config import ProviderRouteConfig
from app.models.research import (
    ResearchRun,
    ResearchRunStatus,
    ResearchSource,
    KnowledgePattern,
    ReaderInsight,
    TrendReport,
)
from app.models.evolution_auto import (
    PromptEvolutionPolicy,
    PromptEvolutionRun,
    PromptEvolutionRunStatus,
)
from app.models.editor import EditorDirective, BookState

__all__ = [
    "Project",
    "NovelBible",
    "Book",
    "BookChapter",
    # Book Analysis models (B3)
    "BookAnalysisProfile",
    "ProjectStyleProfile",
    # Consistency models (B4)
    "ConsistencyRule",
    "ConsistencyCheckResult",
    "ConsistencyIssue",
    "ConsistencyCheckType",
    "ConsistencyIssueSeverity",
    "CharacterConsistencyLog",
    "TimelineEvent",
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
    # Review models (P4 Phase 4)
    "ReviewProfile",
    "ReviewResult",
    "FinalReview",
    # Production models (P4 Phase 5)
    "ProductionPolicy",
    "ProductionLog",
    "ProductionStats",
    "PromptTemplate",
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
    "ConsolidatedMemory",
    # Agent Run models (P0)
    "AgentRun",
    "AgentRunStatus",
    "AgentRunMode",
    "AgentPlan",
    "AgentPlanStatus",
    "AgentStep",
    "AgentStepStatus",
    "SubAgentTask",
    "SubAgentTaskStatus",
    "SubAgentResult",
    "SubAgentResultStatus",
    # Provider Route models (P0)
    "ProviderRouteConfig",
    # Research models (P1)
    "ResearchRun",
    "ResearchRunStatus",
    "ResearchSource",
    "KnowledgePattern",
    "ReaderInsight",
    "TrendReport",
    # Evolution Auto models (P1)
    "PromptEvolutionPolicy",
    "PromptEvolutionRun",
    "PromptEvolutionRunStatus",
    # Editor / BookState models (P2)
    "EditorDirective",
    "BookState",
]
