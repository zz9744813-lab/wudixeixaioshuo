"""
KnowledgeContextService 单元测试 (P1)
"""

from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.research import KnowledgePattern, ReaderInsight
from app.services.knowledge_context_service import KnowledgeContextService


def _seed(db_session: Session) -> int:
    project = Project(name="知识项目", genre="玄幻", status="active")
    db_session.add(project)
    db_session.commit()

    db_session.add(KnowledgePattern(
        genre="玄幻",
        pattern_name="开局打脸",
        pattern_type="opening",
        description="主角开局被轻视，随后反转打脸建立爽点。",
        applicable_scene="第一章",
        anti_patterns="不要拖沓超过2000字",
        confidence=0.9,
    ))
    db_session.add(ReaderInsight(
        genre="玄幻",
        insight_type="dislike",
        title="忌讳主角圣母",
        description="读者反感主角无原则原谅敌人。",
        evidence="多平台评论高频差评",
        confidence=0.8,
    ))
    db_session.commit()
    return project.id


def test_get_context_returns_patterns_and_insights(db_session: Session):
    project_id = _seed(db_session)
    service = KnowledgeContextService(db_session)
    ctx = service.get_context_for_chapter(project_id=project_id, chapter_index=1)

    assert len(ctx["patterns"]) == 1
    assert ctx["patterns"][0]["pattern_name"] == "开局打脸"
    assert len(ctx["reader_insights"]) == 1
    assert ctx["reader_insights"][0]["title"] == "忌讳主角圣母"


def test_format_for_prompt_draft_and_critic(db_session: Session):
    project_id = _seed(db_session)
    service = KnowledgeContextService(db_session)
    ctx = service.get_context_for_chapter(project_id=project_id, chapter_index=1)

    draft_text = service.format_for_prompt(ctx, role="draft")
    assert "## 联网研究知识" in draft_text
    assert "可用套路" in draft_text
    assert "读者避坑" in draft_text

    critic_text = service.format_for_prompt(ctx, role="critic")
    assert "## 联网研究审稿依据" in critic_text


def test_empty_context_returns_blank(db_session: Session):
    project = Project(name="空项目", genre="科幻", status="active")
    db_session.add(project)
    db_session.commit()

    service = KnowledgeContextService(db_session)
    ctx = service.get_context_for_chapter(project_id=project.id, chapter_index=1)
    assert ctx["patterns"] == []
    assert service.format_for_prompt(ctx) == ""
