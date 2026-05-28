"""
Tasks Router - 任务路由
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.task import GenerationTask, GenerationStep, TaskStatus, TaskType

router = APIRouter()


# Pydantic 模型
class TaskCreate(BaseModel):
    project_id: int
    chapter_id: Optional[int] = None
    task_type: str
    priority: int = 2


class TaskResponse(BaseModel):
    id: int
    project_id: int
    chapter_id: Optional[int]
    task_type: str
    status: str
    priority: int
    created_at: Optional[str]
    started_at: Optional[str]
    finished_at: Optional[str]

    class Config:
        from_attributes = True


@router.get("/", response_model=List[TaskResponse])
async def list_tasks(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    project_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """获取任务列表"""
    query = db.query(GenerationTask)
    if status:
        query = query.filter(GenerationTask.status == status)
    if project_id:
        query = query.filter(GenerationTask.project_id == project_id)

    tasks = query.order_by(GenerationTask.created_at.desc()).offset(skip).limit(limit).all()

    return [
        {
            "id": t.id,
            "project_id": t.project_id,
            "chapter_id": t.chapter_id,
            "task_type": t.task_type,
            "status": t.status,
            "priority": t.priority,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "started_at": t.started_at.isoformat() if t.started_at else None,
            "finished_at": t.finished_at.isoformat() if t.finished_at else None,
        }
        for t in tasks
    ]


@router.post("/")
async def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    """创建任务"""
    db_task = GenerationTask(
        project_id=task.project_id,
        chapter_id=task.chapter_id,
        task_type=task.task_type,
        status=TaskStatus.PENDING,
        priority=task.priority,
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)

    return {
        "id": db_task.id,
        "project_id": db_task.project_id,
        "task_type": db_task.task_type,
        "status": db_task.status,
    }


@router.get("/{task_id}")
async def get_task(task_id: int, db: Session = Depends(get_db)):
    """获取任务详情"""
    task = db.query(GenerationTask).filter(GenerationTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return {
        "id": task.id,
        "project_id": task.project_id,
        "chapter_id": task.chapter_id,
        "task_type": task.task_type,
        "status": task.status,
        "priority": task.priority,
        "target_agent": task.target_agent,
        "token_used": task.token_used,
        "estimated_cost": task.estimated_cost,
        "actual_cost": task.actual_cost,
        "error_message": task.error_message,
        "retry_count": task.retry_count,
        "steps": [
            {
                "id": s.id,
                "step_index": s.step_index,
                "agent_name": s.agent_name,
                "score": s.score,
                "model_name": s.model_name,
                "duration_seconds": s.duration_seconds,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in task.steps
        ],
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
    }


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: int, db: Session = Depends(get_db)):
    """取消任务"""
    task = db.query(GenerationTask).filter(GenerationTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status == TaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="已完成的任务无法取消")

    task.status = TaskStatus.CANCELLED
    from datetime import datetime
    task.finished_at = datetime.utcnow()
    db.commit()

    return {"message": "任务已取消", "id": task.id}


@router.post("/{task_id}/retry")
async def retry_task(task_id: int, db: Session = Depends(get_db)):
    """重试任务"""
    task = db.query(GenerationTask).filter(GenerationTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    task.status = TaskStatus.PENDING
    task.retry_count += 1
    task.error_message = None
    db.commit()

    return {"message": "任务已重置", "id": task.id}


@router.get("/{task_id}/steps/{step_id}")
async def get_step(step_id: int, db: Session = Depends(get_db)):
    """获取步骤详情"""
    step = db.query(GenerationStep).filter(GenerationStep.id == step_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="步骤不存在")

    return {
        "id": step.id,
        "task_id": step.task_id,
        "chapter_id": step.chapter_id,
        "step_index": step.step_index,
        "agent_name": step.agent_name,
        "input_prompt": step.input_prompt,
        "raw_output": step.raw_output,
        "parsed_output": step.parsed_output,
        "score": step.score,
        "score_breakdown": step.score_breakdown,
        "model_name": step.model_name,
        "provider_name": step.provider_name,
        "input_tokens": step.input_tokens,
        "output_tokens": step.output_tokens,
        "duration_seconds": step.duration_seconds,
        "error_message": step.error_message,
        "artifact_path": step.artifact_path,
        "created_at": step.created_at.isoformat() if step.created_at else None,
    }
