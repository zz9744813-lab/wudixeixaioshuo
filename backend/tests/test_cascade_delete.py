"""
Cascade Delete Tests
级联删除测试
"""

import pytest
from sqlalchemy.orm import Session

from app.models.chapter import Chapter
from app.models.memory import ChapterMemory, CharacterMemory
from app.models.project import Project
from app.models.task import GenerationTask


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
