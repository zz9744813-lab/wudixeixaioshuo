"""
P5 章节完成后钩子链测试
验证固化失败不影响章节任务成功，且第11章 Prompt 出现"长期固化记忆"。
"""

import asyncio

from sqlalchemy.orm import Session

import app.services.pipeline_service as pipeline_module
from app.models.chapter import Chapter, ChapterStatus
from app.models.memory import ConsolidatedMemory
from app.models.project import Project
from app.services.pipeline_service import PipelineService


def _make_project_chapter(db_session: Session) -> dict:
    project = Project(name="钩子项目", genre="玄幻", status="active")
    db_session.add(project)
    db_session.commit()
    chapter = Chapter(project_id=project.id, chapter_index=11, title="第十一章",
                      status=ChapterStatus.COMPLETED)
    db_session.add(chapter)
    db_session.commit()
    return {
        "project_id": project.id,
        "chapter_id": chapter.id,
        "chapter_index": 11,
        "chapter_title": "第十一章",
        "task_id": 1,
    }


def test_post_hooks_complete_without_raising(db_session, monkeypatch):
    monkeypatch.setattr(pipeline_module, "SessionLocal", lambda: db_session)
    task_info = _make_project_chapter(db_session)
    service = PipelineService()

    async def _noop(*args, **kwargs):
        return None

    # 各子钩子置空，验证钩子链整体顺利跑完
    monkeypatch.setattr(service, "_update_long_term_memory", _noop)
    monkeypatch.setattr(service, "_update_memory_embeddings", _noop)
    monkeypatch.setattr(service, "_consolidate_memory_if_needed", _noop)
    monkeypatch.setattr(service, "_update_book_state", _noop)

    asyncio.run(service._post_chapter_success_hooks(task_info, {"final_content": "正文"}))


def test_consolidate_hook_swallows_error(db_session, monkeypatch):
    monkeypatch.setattr(pipeline_module, "SessionLocal", lambda: db_session)
    task_info = _make_project_chapter(db_session)
    service = PipelineService()

    # _consolidate_memory_if_needed 内部已 try/except，制造 service 抛错验证不外泄
    from app.services import memory_consolidation_service as mcs

    class _BoomService:
        def __init__(self, db):
            pass

        async def consolidate_if_needed(self, **kwargs):
            raise RuntimeError("固化炸了")

    monkeypatch.setattr(mcs, "MemoryConsolidationService", _BoomService)

    # 不应抛出
    asyncio.run(service._consolidate_memory_if_needed(task_info))


def test_consolidated_recall_appears_in_prompt(db_session, monkeypatch):
    monkeypatch.setattr(pipeline_module, "SessionLocal", lambda: db_session)
    task_info = _make_project_chapter(db_session)

    # 预置一条带向量的固化记忆
    db_session.add(ConsolidatedMemory(
        project_id=task_info["project_id"],
        scope_type="volume", scope_start_chapter=1, scope_end_chapter=10,
        title="第1-10章 固化记忆", summary="主角崛起，埋下青铜铃伏笔。",
        embedding_text="主角崛起 青铜铃 伏笔",
        embedding_vector=[1.0, 0.0, 0.0],
        embedding_model="fake",
    ))
    db_session.commit()

    from app.services.memory_service import MemoryService
    service = MemoryService(db_session)

    async def _fake_embed_text(text, model_name=None):
        return [1.0, 0.0, 0.0]

    # patch 语义检索用到的 embedding
    from app.services import memory_semantic_search_service as msss

    orig_init = msss.MemorySemanticSearchService.__init__

    def _patched_init(self, db):
        orig_init(self, db)
        self.embedding_service.embed_text = _fake_embed_text

    monkeypatch.setattr(msss.MemorySemanticSearchService, "__init__", _patched_init)

    context = asyncio.run(service.assemble_context_for_chapter_semantic(
        project_id=task_info["project_id"],
        chapter_index=11,
        chapter_title="青铜铃再响",
    ))
    text = service.format_semantic_recall_for_prompt(context)
    assert "长期固化记忆" in text
    assert "青铜铃" in text
