import pytest
from sqlalchemy.orm import Session

from app.models.research import (
    KnowledgePattern,
    ReaderInsight,
    ResearchRun,
    ResearchRunStatus,
    TrendReport,
)
from app.services.research_agent_service import ResearchAgentService


@pytest.mark.asyncio
async def test_research_agent_creates_run(db_session: Session, monkeypatch):
    """测试研究 Agent 能创建研究运行记录。"""
    monkeypatch.setattr(
        "app.services.web_search_service.WebSearchService.is_configured",
        property(lambda self: False),
    )

    service = ResearchAgentService(db_session)
    run = await service.run_research(
        topic="东方修仙 系统流",
        research_type="pattern",
    )

    assert run.id is not None
    assert run.topic == "东方修仙 系统流"
    assert run.research_type == "pattern"
    assert run.status in [ResearchRunStatus.SUCCEEDED, ResearchRunStatus.FAILED]


@pytest.mark.asyncio
async def test_research_agent_fallback_without_search_api(db_session: Session, monkeypatch):
    """测试无搜索 API 时使用兜底模式。"""
    service = ResearchAgentService(db_session)
    run = await service.run_research(
        topic="都市异能",
        research_type="comment",
    )

    assert run.id is not None
    assert run.status in [ResearchRunStatus.SUCCEEDED, ResearchRunStatus.FAILED]


def test_research_build_queries():
    """测试搜索词生成。"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.database import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    service = ResearchAgentService(db)
    queries = service._build_queries("东方修仙", "pattern")

    assert len(queries) > 0
    assert all("东方修仙" in q for q in queries)
    assert any("套路" in q for q in queries)


def test_research_fallback_extract():
    """测试兜底知识抽取。"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.database import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    service = ResearchAgentService(db)
    result = service._fallback_extract("pattern", "东方修仙")

    assert "patterns" in result
    assert len(result["patterns"]) > 0
    assert result["patterns"][0]["genre"] == "东方修仙"


@pytest.mark.asyncio
async def test_knowledge_service_save_patterns(db_session: Session):
    """测试知识模式保存。"""
    from app.services.knowledge_service import KnowledgeService

    service = KnowledgeService(db_session)
    patterns = [
        {
            "pattern_name": "测试模式",
            "pattern_type": "hook",
            "genre": "测试题材",
            "description": "这是一个测试模式",
            "confidence": 0.8,
        }
    ]

    saved = await service.save_patterns(patterns)
    assert len(saved) == 1
    assert saved[0].pattern_name == "测试模式"


@pytest.mark.asyncio
async def test_knowledge_service_dedup(db_session: Session):
    """测试知识去重。"""
    from app.services.knowledge_service import KnowledgeService

    service = KnowledgeService(db_session)
    patterns = [
        {
            "pattern_name": "去重测试",
            "pattern_type": "hook",
            "genre": "去重题材",
            "description": "第一次保存",
            "confidence": 0.5,
        }
    ]

    saved1 = await service.save_patterns(patterns)
    patterns[0]["confidence"] = 0.9
    saved2 = await service.save_patterns(patterns)

    assert saved1[0].id == saved2[0].id
    assert saved2[0].confidence == 0.9
