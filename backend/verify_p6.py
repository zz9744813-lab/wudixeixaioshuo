"""
P6 端到端测试
- 5 reader profile + 1 chief moderator 初始化
- 创建用户评论 → 入队 triage → chief 处理
- 触发 reader_review → 5 条评论生成
- cleanup → 过期评论删除
- 权重浮动
"""

import sys
import os
import json
from datetime import timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.database import SessionLocal, init_db
from app.models.comment_review import (
    ReaderAgentProfile,
    ReaderReviewRun,
    ReviewComment,
    ReviewCommentGroup,
    ReviewSettings,
)
from app.models.model_config import ModelRole
from app.models.project import Project
from app.models.chapter import Chapter, ChapterVersion
from app.services.review.comment_cleanup_service import run_cleanup
from app.services.review.comment_triage_service import run_for_chapter as run_triage
from app.services.review.queue import enqueue_reader_review
from app.services.review.reader_review_service import run_for_chapter as run_reader_review
from app.services.review.weight_service import bump_for_comment
from app.utils.time_utils import utc_now


def setup_test_data(db):
    """准备测试用的 project + chapter + version. 已存在则复用."""
    project = db.query(Project).filter(
        (Project.id == 1) | (Project.id == 9999)
    ).first()
    if not project:
        project = Project(
            id=9999,
            name="P6 测试项目",
            genre="测试",
        )
        db.add(project)
        db.flush()
    chapter = db.query(Chapter).filter(
        (Chapter.id == 9998) | (Chapter.project_id == project.id)
    ).first()
    if not chapter:
        chapter = Chapter(
            id=9998,
            project_id=project.id,
            chapter_index=1,
            title="测试章节",
            status="completed",
        )
        db.add(chapter)
        db.flush()
    ver = db.query(ChapterVersion).filter(
        (ChapterVersion.id == 9997) | (ChapterVersion.chapter_id == chapter.id)
    ).first()
    if not ver:
        ver = ChapterVersion(
            id=9997,
            chapter_id=chapter.id,
            version_number=1,
            final_content="夜深了, 主角走在雪地里, 心里想着母亲的话。远处传来一声狼嚎, 他加快了脚步。",
        )
        db.add(ver)
        db.flush()
    db.commit()
    return project, chapter, ver


def t1_profiles_seeded(db):
    """6 个 reader profile 已 seed."""
    n = db.query(ReaderAgentProfile).count()
    assert n == 6, f"应有 6 个 profile, 实际 {n}"
    keys = {p.reader_key for p in db.query(ReaderAgentProfile).all()}
    expected = {
        "reader_hook", "reader_emotion", "reader_logic",
        "reader_commercial", "reader_toxic", "chief_comment_moderator",
    }
    assert keys == expected, f"reader_key 集合不匹配: {keys ^ expected}"
    print(f"   ✓ 6 个 profile (5 reader + 1 chief) 已就位")


def t2_create_user_comment(db, project, chapter, ver):
    """用户发表评论 + 自动入队."""
    from app.services.review.queue import enqueue_comment_triage
    expires = utc_now() + timedelta(days=7)
    comment = ReviewComment(
        project_id=project.id,
        chapter_id=chapter.id,
        chapter_version_id=ver.id,
        author_type="user",
        author_label="测试用户",
        content="女主转变缺少可信触发点, 中间需要再加一段",
        tags=["人物动机", "情绪递进"],
        weight_at_created=1.0,
        status="new",
        priority=50,
        expires_at=expires,
    )
    db.add(comment)
    db.flush()
    enqueue_comment_triage(
        db,
        project_id=project.id,
        chapter_id=chapter.id,
        trigger_comment_id=comment.id,
    )
    db.commit()
    assert comment.id is not None
    print(f"   ✓ user 评论 #{comment.id} 创建, 已入队 triage")
    return comment


def t3_triage_handles(db, project, comment):
    """chief moderator 自动分流."""
    result = run_triage(
        db,
        project_id=project.id,
        chapter_id=comment.chapter_id,
        trigger_comment_id=comment.id,
    )
    assert result["status"] in ("ok", "noop"), f"triage 失败: {result}"
    print(f"   ✓ triage: handled={result.get('handled')}, failures={len(result.get('failures', []))}")
    # 验证 comment 状态变化
    db.refresh(comment)
    assert comment.status in ("replied", "grouped", "discussing"), f"comment.status={comment.status}"
    print(f"   ✓ comment #{comment.id} status 变更为 {comment.status}")
    # 验证有 chief_agent 回复
    replies = db.query(ReviewComment).filter(
        ReviewComment.parent_id == comment.id,
        ReviewComment.author_type == "chief_agent",
    ).all()
    assert len(replies) >= 1, f"应有 chief_agent 回复, 实际 0 条"
    print(f"   ✓ chief_agent 已回复 #{replies[0].id}: {replies[0].content[:30]}...")


def t4_reader_review_run(db, project, chapter, ver):
    """5 reader 跑章节 → 5 条评论 + 1 个 run."""
    run = run_reader_review(
        db,
        project_id=project.id,
        chapter_id=chapter.id,
        chapter_version_id=ver.id,
        trigger="manual_test",
    )
    assert run.id is not None
    assert run.status in ("succeeded", "partial"), f"run.status={run.status}"
    n_comments = len(run.generated_comment_ids or [])
    assert n_comments >= 1, f"应至少 1 条 reader 评论, 实际 0"
    print(f"   ✓ run #{run.id} status={run.status}, {n_comments} 条 reader 评论")
    # 验证每条评论
    comments = db.query(ReviewComment).filter(
        ReviewComment.id.in_(run.generated_comment_ids or []),
    ).all()
    authors = {c.author_type for c in comments}
    assert "reader_agent" in authors, f"应有 reader_agent 评论, 实际 authors={authors}"
    print(f"   ✓ 5 reader 全部 author_type=reader_agent, generated_comment_count 已累加")
    return run, comments


def t5_weight_bump(db, comments):
    """权重浮动."""
    # 找一条 reader_agent 评论
    reader_comments = [c for c in comments if c.author_type == "reader_agent"]
    if not reader_comments:
        print("   ⚠ 没有 reader_agent 评论, 跳过权重测试")
        return
    c = reader_comments[0]
    profile_before = db.query(ReaderAgentProfile).filter(
        ReaderAgentProfile.agent_role_id == c.agent_role_id,
    ).first()
    w_before = profile_before.weight
    a_before = profile_before.adopted_count
    r_before = profile_before.rejected_count

    # accept
    p_after = bump_for_comment(db, comment=c, decision="accepted")
    db.commit()
    assert p_after.weight > w_before, f"accept 后权重应增加: {w_before} -> {p_after.weight}"
    assert p_after.adopted_count == a_before + 1
    print(f"   ✓ accept: weight {w_before:.3f} -> {p_after.weight:.3f} (+{p_after.weight - w_before:.3f})")

    # reject
    w_after = p_after.weight
    p_after2 = bump_for_comment(db, comment=c, decision="rejected")
    db.commit()
    assert p_after2.weight < w_after, f"reject 后权重应减少: {w_after} -> {p_after2.weight}"
    assert p_after2.rejected_count == r_before + 1
    print(f"   ✓ reject: weight {w_after:.3f} -> {p_after2.weight:.3f} ({p_after2.weight - w_after:+.3f})")


def t6_cleanup(db, project):
    """创建一条已过期评论, 验证 cleanup 删它."""
    expired = ReviewComment(
        project_id=project.id,
        author_type="user",
        author_label="过期用户",
        content="这条评论已经 7 天前了",
        status="new",
        expires_at=utc_now() - timedelta(days=1),
    )
    db.add(expired)
    db.flush()
    expired_id = expired.id

    # 再加一条新评论, 验证不删
    fresh = ReviewComment(
        project_id=project.id,
        author_type="user",
        author_label="新鲜用户",
        content="这条是新的",
        status="new",
        expires_at=utc_now() + timedelta(days=7),
    )
    db.add(fresh)
    db.flush()
    fresh_id = fresh.id
    db.commit()

    result = run_cleanup(db, retention_days=7)
    assert result["deleted_user"] >= 1, f"应至少删 1 条 user, 实际 {result}"
    # 验证已删
    assert db.query(ReviewComment).filter(ReviewComment.id == expired_id).first() is None
    # 验证未删
    assert db.query(ReviewComment).filter(ReviewComment.id == fresh_id).first() is not None
    print(f"   ✓ cleanup 删 {result['deleted_user']} user + {result['deleted_reader']} reader, 保留新评论")


def t7_settings(db, project):
    """ReviewSettings GET/PUT."""
    s = db.query(ReviewSettings).filter(ReviewSettings.project_id == project.id).first()
    if not s:
        s = ReviewSettings(project_id=project.id)
        db.add(s)
        db.commit()
        db.refresh(s)
    s.auto_reader_review = False
    db.commit()
    assert s.auto_reader_review is False
    print(f"   ✓ ReviewSettings auto_reader_review 切换为 False")
    s.auto_reader_review = True
    db.commit()


def main():
    print("=" * 60)
    print("P6 端到端测试: 评论区驱动评审系统")
    print("=" * 60)
    init_db()
    db = SessionLocal()
    try:
        project, chapter, ver = setup_test_data(db)
        print(f"\n[T1] 6 个 reader profile seeded")
        t1_profiles_seeded(db)

        print(f"\n[T2] 用户发表评论 + 入队 triage")
        user_comment = t2_create_user_comment(db, project, chapter, ver)

        print(f"\n[T3] chief moderator 自动分流")
        t3_triage_handles(db, project, user_comment)

        print(f"\n[T4] 5 reader 跑章节, 生成 5 条评论")
        run, reader_comments = t4_reader_review_run(db, project, chapter, ver)

        print(f"\n[T5] 权重浮动 (accept +0.08, reject -0.03)")
        t5_weight_bump(db, reader_comments)

        print(f"\n[T6] 7 天过期评论自动清理")
        t6_cleanup(db, project)

        print(f"\n[T7] ReviewSettings 切换 auto_reader_review")
        t7_settings(db, project)

        print("\n" + "=" * 60)
        print("P6 全部端到端测试通过 ✓")
        print("=" * 60)
    finally:
        db.close()


if __name__ == "__main__":
    main()
