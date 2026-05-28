"""
Agents Router - Agent 路由
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.chapter import Chapter, ChapterStatus
from app.models.task import GenerationStep, GenerationTask, TaskStatus
from app.services.mock_llm_service import mock_llm_service

router = APIRouter()


class GenerateChapterRequest(BaseModel):
    project_id: int
    chapter_index: int
    title: str = ""


@router.get("/status")
async def get_agent_status(db: Session = Depends(get_db)):
    """获取 Agent 运行状态"""
    running_tasks = db.query(GenerationTask).filter(
        GenerationTask.status == TaskStatus.RUNNING
    ).count()

    pending_tasks = db.query(GenerationTask).filter(
        GenerationTask.status == TaskStatus.PENDING
    ).count()

    return {
        "status": "running" if running_tasks > 0 else "idle",
        "running_tasks": running_tasks,
        "pending_tasks": pending_tasks,
        "agents": [
            {"name": "Planner", "status": "ready", "description": "规划章节内容"},
            {"name": "Draft", "status": "ready", "description": "起草章节初稿"},
            {"name": "Critic", "status": "ready", "description": "多维度审稿评分"},
            {"name": "Rewrite", "status": "ready", "description": "按意见改稿"},
            {"name": "Continuity", "status": "ready", "description": "检查连续性"},
            {"name": "Learning", "status": "ready", "description": "总结经验"},
        ]
    }


@router.post("/generate-chapter")
async def generate_chapter(request: GenerateChapterRequest, db: Session = Depends(get_db)):
    """生成章节（演示完整流程）"""

    # 创建章节
    chapter = Chapter(
        project_id=request.project_id,
        chapter_index=request.chapter_index,
        title=request.title or f"第{request.chapter_index}章",
        status=ChapterStatus.DRAFTING,
    )
    db.add(chapter)
    db.commit()
    db.refresh(chapter)

    # 创建任务
    task = GenerationTask(
        project_id=request.project_id,
        chapter_id=chapter.id,
        task_type="draft",
        status=TaskStatus.RUNNING,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # 模拟完整流程
    import asyncio

    steps_data = []

    # Step 1: Planner
    await asyncio.sleep(0.5)
    planner_response = await mock_llm_service.generate(
        prompt=f"规划第{request.chapter_index}章",
        role="planner"
    )
    step1 = GenerationStep(
        task_id=task.id,
        chapter_id=chapter.id,
        step_index=1,
        agent_name="Planner",
        input_prompt=f"规划第{request.chapter_index}章",
        raw_output=planner_response["content"],
        parsed_output=planner_response["content"],
        model_name=planner_response["model"],
        provider_name=planner_response["provider"],
        input_tokens=planner_response["input_tokens"],
        output_tokens=planner_response["output_tokens"],
        duration_seconds=int(planner_response["duration_seconds"]),
    )
    db.add(step1)
    steps_data.append({
        "agent": "Planner",
        "status": "completed",
        "tokens": planner_response["total_tokens"],
    })

    # Step 2: Draft
    await asyncio.sleep(0.5)
    draft_response = await mock_llm_service.generate(
        prompt=f"起草第{request.chapter_index}章",
        role="draft"
    )
    step2 = GenerationStep(
        task_id=task.id,
        chapter_id=chapter.id,
        step_index=2,
        agent_name="Draft",
        input_prompt=f"起草第{request.chapter_index}章",
        raw_output=draft_response["content"],
        parsed_output=draft_response["content"],
        model_name=draft_response["model"],
        provider_name=draft_response["provider"],
        input_tokens=draft_response["input_tokens"],
        output_tokens=draft_response["output_tokens"],
        duration_seconds=int(draft_response["duration_seconds"]),
    )
    db.add(step2)
    chapter.draft_content = draft_response["content"]
    steps_data.append({
        "agent": "Draft",
        "status": "completed",
        "tokens": draft_response["total_tokens"],
    })

    # Step 3: Critic
    await asyncio.sleep(0.5)
    critic_response = await mock_llm_service.generate(
        prompt=f"审稿第{request.chapter_index}章",
        role="critic"
    )
    step3 = GenerationStep(
        task_id=task.id,
        chapter_id=chapter.id,
        step_index=3,
        agent_name="Critic",
        input_prompt=f"审稿第{request.chapter_index}章",
        raw_output=critic_response["content"],
        parsed_output=critic_response["content"],
        score=82.0,
        model_name=critic_response["model"],
        provider_name=critic_response["provider"],
        input_tokens=critic_response["input_tokens"],
        output_tokens=critic_response["output_tokens"],
        duration_seconds=int(critic_response["duration_seconds"]),
    )
    db.add(step3)
    chapter.total_score = 82.0
    steps_data.append({
        "agent": "Critic",
        "status": "completed",
        "score": 82,
        "tokens": critic_response["total_tokens"],
    })

    # Step 4: Rewrite (如果分数不够高)
    if chapter.total_score < 85:
        await asyncio.sleep(0.5)
        rewrite_response = await mock_llm_service.generate(
            prompt=f"改稿第{request.chapter_index}章",
            role="rewrite"
        )
        step4 = GenerationStep(
            task_id=task.id,
            chapter_id=chapter.id,
            step_index=4,
            agent_name="Rewrite",
            input_prompt=f"改稿第{request.chapter_index}章",
            raw_output=rewrite_response["content"],
            parsed_output=rewrite_response["content"],
            model_name=rewrite_response["model"],
            provider_name=rewrite_response["provider"],
            input_tokens=rewrite_response["input_tokens"],
            output_tokens=rewrite_response["output_tokens"],
            duration_seconds=int(rewrite_response["duration_seconds"]),
        )
        db.add(step4)
        chapter.draft_content = rewrite_response["content"]
        steps_data.append({
            "agent": "Rewrite",
            "status": "completed",
            "tokens": rewrite_response["total_tokens"],
        })

    # Step 5: Continuity
    await asyncio.sleep(0.5)
    continuity_response = await mock_llm_service.generate(
        prompt=f"检查连续性第{request.chapter_index}章",
        role="continuity"
    )
    step5 = GenerationStep(
        task_id=task.id,
        chapter_id=chapter.id,
        step_index=5,
        agent_name="Continuity",
        input_prompt=f"检查连续性第{request.chapter_index}章",
        raw_output=continuity_response["content"],
        parsed_output=continuity_response["content"],
        score=90.0,
        model_name=continuity_response["model"],
        provider_name=continuity_response["provider"],
        input_tokens=continuity_response["input_tokens"],
        output_tokens=continuity_response["output_tokens"],
        duration_seconds=int(continuity_response["duration_seconds"]),
    )
    db.add(step5)
    chapter.continuity_score = 90.0
    steps_data.append({
        "agent": "Continuity",
        "status": "completed",
        "score": 90,
        "tokens": continuity_response["total_tokens"],
    })

    # 完成任务
    chapter.status = ChapterStatus.COMPLETED
    chapter.final_content = chapter.draft_content
    chapter.final_word_count = len(chapter.final_content)
    from datetime import datetime
    chapter.completed_at = datetime.utcnow()

    task.status = TaskStatus.COMPLETED
    task.finished_at = datetime.utcnow()

    db.commit()

    return {
        "message": "章节生成完成",
        "chapter_id": chapter.id,
        "final_score": chapter.total_score,
        "word_count": chapter.final_word_count,
        "steps": steps_data,
    }
