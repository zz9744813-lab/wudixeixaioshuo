"""
P1 真人训练营模型测试
验证 Feedback 扩字段与 FeedbackBatch 模型，且保留原有 parsed_rule/priority/is_applied。
"""

from sqlalchemy.orm import Session

from app.models.chapter import Chapter, ChapterStatus
from app.models.feedback import Feedback, FeedbackBatch
from app.models.project import Project


def _seed(db_session: Session) -> dict:
    project = Project(name="训练营项目", genre="玄幻", status="active")
    db_session.add(project)
    db_session.commit()
    chapter = Chapter(project_id=project.id, chapter_index=1, title="第一章",
                      status=ChapterStatus.COMPLETED)
    db_session.add(chapter)
    db_session.commit()
    return {"project_id": project.id, "chapter_id": chapter.id}


def test_feedback_new_fields(db_session: Session):
    info = _seed(db_session)
    fb = Feedback(
        project_id=info["project_id"], chapter_id=info["chapter_id"],
        source="reader", raw_text="中段解释太多",
        reader_score=78.0,
        dimension_scores={"pacing": 72, "reader_addiction": 85},
        anchor=[{"para": 12, "quote": "他站在原地", "comment": "拖了", "type": "pacing"}],
        reaction="hooked",
        applied_from_chapter=2,
        status="queued",
    )
    db_session.add(fb)
    db_session.commit()
    db_session.refresh(fb)

    assert fb.reader_score == 78.0
    assert fb.dimension_scores["reader_addiction"] == 85
    assert fb.anchor[0]["type"] == "pacing"
    assert fb.reaction == "hooked"
    assert fb.status == "queued"


def test_feedback_legacy_fields_kept(db_session: Session):
    info = _seed(db_session)
    fb = Feedback(
        project_id=info["project_id"], chapter_id=info["chapter_id"],
        source="reader", raw_text="x",
        parsed_rule="旧规则", priority=3, is_applied=1,
    )
    db_session.add(fb)
    db_session.commit()
    db_session.refresh(fb)
    assert fb.parsed_rule == "旧规则"
    assert fb.priority == 3
    assert fb.is_applied == 1


def test_feedback_batch_and_relationship(db_session: Session):
    info = _seed(db_session)
    batch = FeedbackBatch(
        project_id=info["project_id"], chapter_id=info["chapter_id"],
        feedback_ids=[1, 2], feedback_count=2,
        avg_reader_score=76.0, avg_system_score=88.0, critic_gap=-12.0,
        derived_rules=[{"role": "draft", "rule": "前800字出现冲突", "priority": 9}],
        status="processed",
    )
    db_session.add(batch)
    db_session.commit()

    fb = Feedback(
        project_id=info["project_id"], chapter_id=info["chapter_id"],
        source="reader", raw_text="y", status="batched", batch_id=batch.id,
    )
    db_session.add(fb)
    db_session.commit()
    db_session.refresh(batch)

    assert batch.critic_gap == -12.0
    assert batch.derived_rules[0]["priority"] == 9
    assert len(batch.feedbacks) == 1
    assert batch.feedbacks[0].batch.id == batch.id
