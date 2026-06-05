"""
P6 Reader Review Service
- 触发 5 个 reader Agent 读章节
- 每个 reader 输出 1 条 ReviewComment
- 全部写 ReaderReviewRun

简化版: 不调真 LLM (避免依赖完整 P2 链路), 用模板化的 stub 评论。
生产环境应该走 AgentRoleRunner (P6 P2 计划) 调真实模型。
"""

import json
import random
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.chapter import Chapter, ChapterVersion
from app.models.comment_review import (
    ReaderAgentProfile,
    ReaderReviewRun,
    ReviewComment,
    ReviewSettings,
)
from app.models.project import Project
from app.services.review.queue import enqueue_comment_triage
from app.services.review.reader_setup_service import get_enabled_reader_profiles
from app.utils.time_utils import utc_now


# 每个 reader 的 fallback 评论库 (生产用 LLM 生成, 这里用模板)
_READER_FALLBACK_COMMENTS = {
    "reader_hook": [
        {
            "score": 78,
            "comment_title": "开头有点慢热",
            "comment_text": "开头 300 字主要是背景铺陈, 第一个小冲突出现在 35% 处. 建议把核心矛盾提前到 20% 内.",
            "severity": "medium",
            "suggestion": "前 200 字内加一个具体动作或冲突场景",
            "tags": ["开头钩子"],
        },
    ],
    "reader_emotion": [
        {
            "score": 82,
            "comment_title": "情绪递进基本合理",
            "comment_text": "女主态度转变有一条主线, 但中间少了关键触发点. 第 60% 处那句旁白解释「她理解了他」略生硬.",
            "severity": "medium",
            "suggestion": "在 50% 处加一个主角付出代价的具体行为, 让女主转变有据可依",
            "tags": ["人物动机", "情绪递进"],
        },
    ],
    "reader_logic": [
        {
            "score": 88,
            "comment_title": "设定自洽",
            "comment_text": "本章没发现明显设定硬伤. 伏笔 3 推进合理, 数字/时间线都对得上.",
            "severity": "low",
            "suggestion": "继续保持",
            "tags": ["设定自洽"],
        },
    ],
    "reader_commercial": [
        {
            "score": 75,
            "comment_title": "节奏中规中矩",
            "comment_text": "中段有小高潮但释放得有点早, 结尾钩子偏弱. 整体字数 2400, 适合放在低峰位置.",
            "severity": "medium",
            "suggestion": "结尾加一个 50 字内的具体悬念, 不要用旁白点题",
            "tags": ["节奏", "留存"],
        },
    ],
    "reader_toxic": [
        {
            "score": 90,
            "comment_title": "没有明显毒点",
            "comment_text": "没有发现工具人化配角或强行误会. 主角没有过度正确.",
            "severity": "low",
            "suggestion": "继续保持",
            "tags": [],
        },
    ],
}


def _get_chapter_final_text(db: Session, chapter: Chapter) -> str:
    """取章节最新版本正文."""
    ver = db.query(ChapterVersion).filter(
        ChapterVersion.chapter_id == chapter.id,
    ).order_by(ChapterVersion.version_number.desc()).first()
    if ver and ver.final_content:
        return ver.final_content
    return ""


def _get_project_context(db: Session, project: Project) -> str:
    return f"{project.name} | {project.genre or '未分类'}"


def _fallback_comment_for(reader_key: str, chapter_title: str) -> Dict[str, Any]:
    """生产环境应调 LLM, 这里用模板. 每次 chapter 不同, 给点变化."""
    pool = _READER_FALLBACK_COMMENTS.get(reader_key, [])
    if not pool:
        return {
            "score": 75,
            "comment_title": f"{reader_key} 反馈",
            "comment_text": f"对 {chapter_title} 的整体印象尚可, 建议保持当前风格并注意细节.",
            "severity": "low",
            "suggestion": "无",
            "tags": [],
        }
    return random.choice(pool)


def _create_comment_for_reader(
    db: Session,
    *,
    run: ReaderReviewRun,
    profile: ReaderAgentProfile,
    chapter: Chapter,
    project: Project,
    parsed: Dict[str, Any],
) -> ReviewComment:
    expires = utc_now() + __import__("datetime").timedelta(days=7)
    return ReviewComment(
        project_id=project.id,
        chapter_id=chapter.id,
        chapter_version_id=run.chapter_version_id,
        author_type="reader_agent",
        author_label=profile.display_name or profile.reader_key,
        agent_role_id=profile.agent_role_id,
        content=parsed.get("comment_text", ""),
        evidence=parsed.get("evidence"),
        rating={"score": parsed.get("score")},
        tags=parsed.get("tags", []),
        weight_at_created=profile.weight,
        status="new",
        priority=_priority_from_severity(parsed.get("severity", "low")),
        expires_at=expires,
    )


def _priority_from_severity(severity: str) -> int:
    return {
        "blocker": 95,
        "high": 80,
        "medium": 60,
        "low": 30,
    }.get(severity, 50)


def run_for_chapter(
    db: Session,
    *,
    project_id: int,
    chapter_id: int,
    chapter_version_id: Optional[int] = None,
    trigger: str = "chapter_completed",
) -> ReaderReviewRun:
    """5 个 reader 读 1 章, 输出 5 条评论 + 1 个 run 记录."""
    project = db.query(Project).filter(Project.id == project_id).first()
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not project or not chapter:
        raise ValueError(f"Project {project_id} 或 Chapter {chapter_id} 不存在")

    # 检查 ReviewSettings
    settings = db.query(ReviewSettings).filter(
        ReviewSettings.project_id == project_id,
    ).first()
    if settings and not settings.auto_reader_review:
        run = ReaderReviewRun(
            project_id=project_id,
            chapter_id=chapter_id,
            chapter_version_id=chapter_version_id,
            trigger=trigger,
            status="skipped",
            reader_agent_keys=[],
            error="auto_reader_review disabled",
        )
        db.add(run)
        db.commit()
        return run

    readers = get_enabled_reader_profiles(db)
    if not readers:
        run = ReaderReviewRun(
            project_id=project_id,
            chapter_id=chapter_id,
            chapter_version_id=chapter_version_id,
            trigger=trigger,
            status="failed",
            error="no reader profiles found (run seed_p6_reader_agents first)",
        )
        db.add(run)
        db.commit()
        return run

    run = ReaderReviewRun(
        project_id=project_id,
        chapter_id=chapter_id,
        chapter_version_id=chapter_version_id,
        trigger=trigger,
        status="running",
        reader_agent_keys=[r.reader_key for r in readers],
        started_at=utc_now(),
    )
    db.add(run)
    db.flush()

    final_text = _get_chapter_final_text(db, chapter)
    generated_ids: List[int] = []
    succeeded = 0

    for reader in readers:
        try:
            parsed = _fallback_comment_for(reader.reader_key, chapter.title or "")
            comment = _create_comment_for_reader(
                db,
                run=run,
                profile=reader,
                chapter=chapter,
                project=project,
                parsed=parsed,
            )
            db.add(comment)
            db.flush()
            generated_ids.append(comment.id)
            reader.generated_comment_count = (reader.generated_comment_count or 0) + 1
            reader.last_used_at = utc_now()
            succeeded += 1
        except Exception as exc:
            # 单个 reader 失败不影响其他
            print(f"[ReaderReviewService] {reader.reader_key} failed: {exc}")
            continue

    run.status = "succeeded" if succeeded == len(readers) else "partial"
    run.generated_comment_ids = generated_ids
    run.finished_at = utc_now()

    # 触发 comment_triage
    enqueue_comment_triage(
        db,
        project_id=project_id,
        chapter_id=chapter_id,
        trigger_comment_id=generated_ids[0] if generated_ids else None,
    )
    db.commit()
    return run
