"""SubAgent Router - 子 Agent 任务 API。"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.subagent_service import SubAgentService

router = APIRouter(prefix="/subagents", tags=["subagents"])


@router.get("/tasks")
async def list_subagent_tasks(
    run_id: Optional[int] = Query(None, description="按 AgentRun 过滤"),
    status: Optional[str] = Query(None, description="按状态过滤"),
    db: Session = Depends(get_db),
):
    """获取子 Agent 任务列表。"""
    return SubAgentService(db).list_tasks(run_id=run_id, status=status)


@router.get("/tasks/{task_id}")
async def get_subagent_task(task_id: int, db: Session = Depends(get_db)):
    """获取子 Agent 任务详情。"""
    task = SubAgentService(db).get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="子 Agent 任务不存在")
    return task


@router.post("/tasks/{task_id}/retry")
async def retry_subagent_task(task_id: int, db: Session = Depends(get_db)):
    """重试子 Agent 任务。"""
    try:
        task = await SubAgentService(db).retry_task(task_id)
        return SubAgentService(db).serialize_task(task)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/cancel")
async def cancel_subagent_task(task_id: int, db: Session = Depends(get_db)):
    """取消子 Agent 任务。"""
    success = await SubAgentService(db).cancel_task(task_id)
    if not success:
        raise HTTPException(status_code=400, detail="无法取消子 Agent 任务")
    return {"message": "子 Agent 任务已取消", "task_id": task_id}


@router.get("/runs/{run_id}/tree")
async def get_subagent_run_tree(run_id: int, db: Session = Depends(get_db)):
    """获取某次运行的子任务树。"""
    try:
        return SubAgentService(db).get_run_tree(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/runs/{run_id}/summary")
async def get_subagent_run_summary(run_id: int, db: Session = Depends(get_db)):
    """汇总某次运行的子 Agent 结果。"""
    return SubAgentService(db).reduce_results(run_id)
