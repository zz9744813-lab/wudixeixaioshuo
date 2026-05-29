"""
Schemas - Pydantic 数据模型
"""

from app.schemas.common import ApiResponse, ErrorResponse, HealthCheck, PageResponse
from app.schemas.project import (
    NovelBibleOut,
    NovelBibleUpdate,
    ProjectCreate,
    ProjectList,
    ProjectOut,
    ProjectUpdate,
)
from app.schemas.chapter import (
    ChapterCreate,
    ChapterList,
    ChapterOut,
    ChapterUpdate,
    ChapterVersionOut,
)
from app.schemas.task import (
    GenerationStepOut,
    GenerationTaskDetail,
    GenerationTaskOut,
    TaskCreate,
    TaskList,
    TaskStatusUpdate,
)
from app.schemas.worker import (
    AgentStepOut,
    WorkerControlRequest,
    WorkerEventOut,
    WorkerStatusOut,
)
from app.schemas.book import (
    BookCreate,
    BookDetail,
    BookOut,
    BookUploadResponse,
)

__all__ = [
    # Common
    "ApiResponse",
    "ErrorResponse",
    "HealthCheck",
    "PageResponse",
    # Project
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectOut",
    "ProjectList",
    "NovelBibleOut",
    "NovelBibleUpdate",
    # Chapter
    "ChapterCreate",
    "ChapterUpdate",
    "ChapterOut",
    "ChapterList",
    "ChapterVersionOut",
    # Task
    "GenerationTaskOut",
    "GenerationTaskDetail",
    "GenerationStepOut",
    "TaskCreate",
    "TaskList",
    "TaskStatusUpdate",
    # Worker
    "WorkerStatusOut",
    "WorkerControlRequest",
    "WorkerEventOut",
    "AgentStepOut",
    # Book
    "BookCreate",
    "BookOut",
    "BookDetail",
    "BookUploadResponse",
]
