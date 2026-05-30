"""
P2 process_pending_batch 测试
验证 waiting/processed 状态、批次创建、derived_rules、critic_gap、规则取用。
"""

import asyncio

from sqlalchemy.orm import Session

import app.services.reader_training_service as rt_module
from app.models.chapter import Chapter, ChapterStatus
from app.models.feedback import Feedback, FeedbackBatch
from app.models.project import Project
from app.services.reader_training_service import (
    ReaderTrainingService,
    format_reader_rules_for_prompt,
)


class _FakeLLM:
    async def generate(self, *a, **k):
        return {
            "content": (
                '{"derived_rules": ['
                '{"role": "draft", "rule": "前800字必须出现冲突", "priority": 9, '
                '"evidence": ["拖了"], "applied_from_chapter": 3},'
                '{"role": "critic", "rule": "严查主角主动性", "priority": 8, '
                '"evidence": [], "applied_from_chapter": 3}'
                '], "dimension_summary": {}, "reaction_summary": {}}'
            ),
            "total_tokens": 10, "cost": 0.0,
        }


def _seed(db_session: Session, n: int, reader_score=76, system_score=88) -> int:
    project = Project(name="批处理项目", genre="玄幻", status="active")
    db_session.add(project)
    db_session.commit()
    chapter = Chapter(project_id=project.id, chapter_index=2, title="第二章",
                      status=ChapterStatus.COMPLETED, total_score=system_score)
    db_session.add(chapter)
    db_session.commit()
    for i in range(n):
        db_session.add(Feedback(
            project_id=project.id, chapter_id=chapter.id, source="reader",
            raw_text=f"反馈{i}", reader_score=reader_score, reaction="meh",
            anchor=[{"para": 1, "quote": "x", "comment": "拖了", "type": "pacing"}],
            status="queued",
        ))
    db_session.commit()
    return project.id


def test_waiting_when_below_min_batch(db_session, monkeypatch):
    monkeypatch.setattr(rt_module, "llm_manager", _FakeLLM())
    project_id = _seed(db_session, n=3)
    service = ReaderTrainingService(db_session)
    result = asyncio.run(service.process_pending_batch(project_id=project_id, min_batch=5))
    assert result["status"] == "waiting"
    assert result["pending_count"] == 3
    assert db_session.query(FeedbackBatch).count() == 0


def test_processed_when_enough(db_session, monkeypatch):
    monkeypatch.setattr(rt_module, "llm_manager", _FakeLLM())
    project_id = _seed(db_session, n=5)
    service = ReaderTrainingService(db_session)
    result = asyncio.run(service.process_pending_batch(project_id=project_id, min_batch=5))

    assert result["status"] == "processed"
    assert result["feedback_count"] == 5
    assert result["derived_rules_count"] >= 2

    batch = db_session.query(FeedbackBatch).filter(
        FeedbackBatch.id == result["batch_id"]
    ).first()
    assert batch.status == "processed"
    fbs = db_session.query(Feedback).filter(Feedback.batch_id == batch.id).all()
    assert len(fbs) == 5
    assert all(f.status == "batched" for f in fbs)


def test_rules_retrievable_for_role(db_session, monkeypatch):
    monkeypatch.setattr(rt_module, "llm_manager", _FakeLLM())
    project_id = _seed(db_session, n=5)
    service = ReaderTrainingService(db_session)
    asyncio.run(service.process_pending_batch(project_id=project_id, min_batch=5))

    draft_rules = service.get_reader_rules_for_prompt(project_id, "draft", chapter_index=5)
    assert len(draft_rules) >= 1
    assert draft_rules[0]["role"] == "draft"

    text = format_reader_rules_for_prompt(draft_rules, "draft")
    assert "真人读者训练营规则" in text

    # applied_from_chapter=3 的规则，对 chapter_index=2 不可见
    early = service.get_reader_rules_for_prompt(project_id, "draft", chapter_index=2)
    assert early == []
