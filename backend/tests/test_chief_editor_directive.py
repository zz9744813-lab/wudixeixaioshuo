"""
ChiefEditorAgent 单元测试 (P2)
验证能生成 EditorDirective，且同一 chapter 重复生成不会重复插入。
"""

import asyncio

from sqlalchemy.orm import Session

import app.services.chief_editor_agent as chief_module
from app.models.chapter import Chapter, ChapterStatus
from app.models.editor import EditorDirective
from app.models.foreshadow import Foreshadow
from app.models.project import Project
from app.services.chief_editor_agent import ChiefEditorAgent


class _FakeLLM:
    async def generate(self, *args, **kwargs):
        return {
            "content": (
                '{"global_position": {"volume": "第一卷", "arc": "入局", '
                '"stage": "升级", "chapter_role": "制造首次失败"}, '
                '"tension_target": {"start_level": 4, "peak_level": 7, '
                '"ending_level": 8, "emotion_curve": "压迫→反抗"}, '
                '"plot_goals": ["推进主线"], "payoff_goals": [], '
                '"foreshadow_goals": ["神秘玉佩"], "character_arc_goals": {}, '
                '"commercial_goals": {"main_hook": "反转", "爽点类型": "打脸", "avoid": []}, '
                '"risk_warnings": []}'
            ),
            "total_tokens": 10,
            "cost": 0.0,
        }


def _seed(db_session: Session) -> dict:
    project = Project(name="总编项目", genre="玄幻", status="active")
    db_session.add(project)
    db_session.commit()
    chapter = Chapter(
        project_id=project.id, chapter_index=2, title="第二章",
        status=ChapterStatus.PLANNED,
    )
    db_session.add(chapter)
    db_session.add(Foreshadow(
        project_id=project.id, title="神秘玉佩", status="ready_to_payoff",
    ))
    db_session.commit()
    return {
        "project_id": project.id,
        "chapter_id": chapter.id,
        "chapter_index": 2,
        "chapter_title": "第二章",
    }


def test_build_directive_creates_record(db_session, monkeypatch):
    monkeypatch.setattr(chief_module, "llm_manager", _FakeLLM())
    info = _seed(db_session)
    agent = ChiefEditorAgent(db_session)

    directive = asyncio.run(agent.build_chapter_directive(**info))

    assert directive["global_position"]["volume"] == "第一卷"
    rows = db_session.query(EditorDirective).filter(
        EditorDirective.chapter_id == info["chapter_id"]
    ).all()
    assert len(rows) == 1
    assert rows[0].formatted_prompt


def test_build_directive_no_duplicate(db_session, monkeypatch):
    monkeypatch.setattr(chief_module, "llm_manager", _FakeLLM())
    info = _seed(db_session)
    agent = ChiefEditorAgent(db_session)

    asyncio.run(agent.build_chapter_directive(**info))
    asyncio.run(agent.build_chapter_directive(**info))

    rows = db_session.query(EditorDirective).filter(
        EditorDirective.chapter_id == info["chapter_id"]
    ).all()
    assert len(rows) == 1


def test_format_directive_for_prompt():
    agent = ChiefEditorAgent(None)
    text = agent.format_directive_for_prompt({
        "global_position": {"volume": "第一卷", "arc": "入局", "stage": "升级", "chapter_role": "失败"},
        "tension_target": {"start_level": 4, "peak_level": 7, "ending_level": 8, "emotion_curve": "压迫"},
        "plot_goals": ["推进主线"],
        "foreshadow_goals": ["神秘玉佩"],
    })
    assert "全局定位" in text
    assert "张力目标" in text
    assert "神秘玉佩" in text
