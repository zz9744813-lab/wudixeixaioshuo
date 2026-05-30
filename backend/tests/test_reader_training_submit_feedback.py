"""
P2 submit_feedback 测试
验证同步快返、不调用 LLM、入队状态、事件发布。
"""

from sqlalchemy.orm import Session

import app.services.reader_training_service as rt_module
from app.models.chapter import Chapter, ChapterStatus
from app.models.feedback import Feedback
from app.models.project import Project
from app.services.reader_training_service import ReaderTrainingService


def _seed(db_session: Session) -> dict:
    project = Project(name="提交项目", genre="玄幻", status="active")
    db_session.add(project)
    db_session.commit()
    chapter = Chapter(project_id=project.id, chapter_index=1, title="第一章",
                      status=ChapterStatus.COMPLETED)
    db_session.add(chapter)
    db_session.commit()
    return {"project_id": project.id, "chapter_id": chapter.id}


def test_submit_feedback_returns_queued(db_session, monkeypatch):
    # 任何 LLM 调用都视为失败：submit 不应触碰 LLM
    class _Boom:
        async def generate(self, *a, **k):
            raise AssertionError("submit_feedback 不应调用 LLM")
    monkeypatch.setattr(rt_module, "llm_manager", _Boom())

    info = _seed(db_session)
    service = ReaderTrainingService(db_session)
    result = service.submit_feedback(
        project_id=info["project_id"], chapter_id=info["chapter_id"],
        reader_score=78, reaction="hooked",
        dimension_scores={"pacing": 72}, raw_comment="中段解释太多",
        min_batch=5,
    )

    assert result["status"] == "queued"
    assert result["feedback_id"] is not None
    assert result["pending_count"] == 1
    assert result["needed_for_batch"] == 4

    fb = db_session.query(Feedback).filter(Feedback.id == result["feedback_id"]).first()
    assert fb.status == "queued"
    assert fb.reader_score == 78


def test_submit_feedback_validates_reaction(db_session):
    info = _seed(db_session)
    service = ReaderTrainingService(db_session)
    try:
        service.submit_feedback(
            project_id=info["project_id"], chapter_id=info["chapter_id"],
            reaction="invalid",
        )
        assert False, "应抛出 ValueError"
    except ValueError:
        pass


def test_submit_feedback_validates_score_range(db_session):
    info = _seed(db_session)
    service = ReaderTrainingService(db_session)
    try:
        service.submit_feedback(
            project_id=info["project_id"], chapter_id=info["chapter_id"],
            reader_score=150,
        )
        assert False, "应抛出 ValueError"
    except ValueError:
        pass
