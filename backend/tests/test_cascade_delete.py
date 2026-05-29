"""
Cascade Delete Tests
级联删除测试 - BE-002
"""

import pytest
from sqlalchemy.orm import Session

from app.models.chapter import Chapter
from app.models.memory import ChapterMemory, CharacterMemory
from app.models.project import Project, NovelBible
from app.models.task import GenerationTask
from app.models.book import Book, BookChapter, BookStatus


def test_delete_project_cascades_chapters(db_session: Session):
    """删除项目应级联删除章节"""
    # 创建项目
    project = Project(
        name="Test Project",
        genre="玄幻",
        status="active",
    )
    db_session.add(project)
    db_session.commit()

    # 创建章节
    chapter = Chapter(
        project_id=project.id,
        chapter_index=1,
        title="Test Chapter",
        status="planned",
    )
    db_session.add(chapter)
    db_session.commit()

    chapter_id = chapter.id

    # 删除项目
    db_session.delete(project)
    db_session.commit()

    # 验证章节已被删除
    remaining = db_session.query(Chapter).filter(Chapter.id == chapter_id).first()
    assert remaining is None


def test_delete_project_cascades_tasks(db_session: Session):
    """删除项目应级联删除任务"""
    # 创建项目
    project = Project(
        name="Test Project 2",
        genre="玄幻",
        status="active",
    )
    db_session.add(project)
    db_session.commit()

    # 先创建章节
    chapter = Chapter(
        project_id=project.id,
        chapter_index=1,
        title="Test Chapter",
        status="planned",
    )
    db_session.add(chapter)
    db_session.commit()

    # 创建任务
    task = GenerationTask(
        project_id=project.id,
        chapter_id=chapter.id,
        task_type="chapter_generation",
        status="pending",
        priority=5,
    )
    db_session.add(task)
    db_session.commit()

    task_id = task.id

    # 删除项目
    db_session.delete(project)
    db_session.commit()

    # 验证任务已被删除
    remaining = db_session.query(GenerationTask).filter(GenerationTask.id == task_id).first()
    assert remaining is None


def test_delete_project_cascades_memory(db_session: Session):
    """删除项目应级联删除记忆数据"""
    # 创建项目
    project = Project(
        name="Test Project 3",
        genre="玄幻",
        status="active",
    )
    db_session.add(project)
    db_session.commit()

    # 创建角色记忆
    char_memory = CharacterMemory(
        project_id=project.id,
        name="Test Character",
    )
    db_session.add(char_memory)
    db_session.commit()

    memory_id = char_memory.id

    # 删除项目
    db_session.delete(project)
    db_session.commit()

    # 验证记忆已被删除
    remaining = db_session.query(CharacterMemory).filter(CharacterMemory.id == memory_id).first()
    assert remaining is None


# ========== BE-002 新增测试 ==========

def test_delete_project_cascades_bible(db_session: Session):
    """BE-002: 删除 Project 必须级联删除关联的 NovelBible"""
    # 创建项目
    project = Project(
        name="测试项目Bible级联",
        genre="玄幻",
        status="active",
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    # 创建 Bible
    bible = NovelBible(
        project_id=project.id,
        world_setting="测试世界观",
        main_plot="测试主线",
    )
    db_session.add(bible)
    db_session.commit()
    db_session.refresh(bible)

    # 验证创建成功
    assert bible.id is not None
    assert bible.project_id == project.id

    bible_id = bible.id

    # 删除 Project
    db_session.delete(project)
    db_session.commit()

    # 验证 Bible 也被删除
    deleted_bible = db_session.query(NovelBible).filter(
        NovelBible.id == bible_id
    ).first()
    assert deleted_bible is None, "Bible 应该被级联删除"


def test_delete_book_cascades_book_chapters(db_session: Session):
    """BE-002: 删除 Book 必须级联删除关联的 BookChapter"""
    # 创建 Book
    book = Book(
        title="测试书籍级联",
        author_alias="测试作者",
        genre="科幻",
        status=BookStatus.IMPORTED,
        total_chapters=0,
    )
    db_session.add(book)
    db_session.commit()
    db_session.refresh(book)

    # 创建多个章节
    chapters = []
    for i in range(3):
        chapter = BookChapter(
            book_id=book.id,
            chapter_index=i + 1,
            title=f"第{i+1}章",
            content=f"第{i+1}章内容",
            word_count=1000,
        )
        db_session.add(chapter)
        chapters.append(chapter)

    db_session.commit()

    # 验证章节创建成功
    for ch in chapters:
        db_session.refresh(ch)
        assert ch.id is not None

    chapter_ids = [ch.id for ch in chapters]

    # 删除 Book
    db_session.delete(book)
    db_session.commit()

    # 验证所有章节也被删除
    for ch_id in chapter_ids:
        deleted_chapter = db_session.query(BookChapter).filter(
            BookChapter.id == ch_id
        ).first()
        assert deleted_chapter is None, f"BookChapter {ch_id} 应该被级联删除"


def test_no_orphan_bible_after_project_delete(db_session: Session):
    """BE-002: 删除 Project 后不应有孤立的 Bible 记录"""
    # 创建项目和 Bible
    project = Project(
        name="临时项目NoOrphan",
        genre="测试",
        status="active",
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    bible = NovelBible(
        project_id=project.id,
        world_setting="临时世界观",
    )
    db_session.add(bible)
    db_session.commit()

    project_id = project.id

    # 删除项目
    db_session.delete(project)
    db_session.commit()

    # 检查是否有孤立的 Bible
    orphan_count = db_session.query(NovelBible).filter(
        NovelBible.project_id == project_id
    ).count()
    assert orphan_count == 0, f"删除 Project 后不应有 {orphan_count} 个孤儿 Bible"


def test_no_orphan_chapters_after_book_delete(db_session: Session):
    """BE-002: 删除 Book 后不应有孤立的 Chapter 记录"""
    # 创建 Book 和 Chapters
    book = Book(
        title="临时书籍NoOrphan",
        genre="测试",
        status=BookStatus.IMPORTED,
    )
    db_session.add(book)
    db_session.commit()
    db_session.refresh(book)

    for i in range(5):
        chapter = BookChapter(
            book_id=book.id,
            chapter_index=i + 1,
            title=f"章节{i+1}",
            content="内容",
        )
        db_session.add(chapter)
    db_session.commit()

    book_id = book.id

    # 删除 Book
    db_session.delete(book)
    db_session.commit()

    # 检查是否有孤立的 Chapters
    orphan_count = db_session.query(BookChapter).filter(
        BookChapter.book_id == book_id
    ).count()
    assert orphan_count == 0, f"删除 Book 后不应有 {orphan_count} 个孤儿 Chapter"

