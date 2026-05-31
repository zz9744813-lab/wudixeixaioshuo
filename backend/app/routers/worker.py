"""
Worker Router - 24小时自动写作 API
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.worker_service import WorkerStatus, worker
from app.services.task_queue_service import TaskQueueService

router = APIRouter()


# ============== 请求模型 ==============

class WorkerControlRequest(BaseModel):
    action: str  # start, stop, pause, resume


class QueueAddRequest(BaseModel):
    project_id: int
    chapter_ids: Optional[list] = None  # None = 添加所有待写作章节


class QueueReorderRequest(BaseModel):
    task_ids: list  # 按新顺序排列的任务ID列表（队列排序对象是任务，不是章节）


# ============== Worker 控制 API ==============

@router.post("/control")
async def control_worker(
    request: WorkerControlRequest,
    db: Session = Depends(get_db)
):
    """
    控制 Worker 状态

    - start: 启动 Worker
    - stop: 停止 Worker
    - pause: 暂停 Worker
    - resume: 恢复 Worker
    """
    action = request.action.lower()

    if action == "start":
        await worker.start()
        return {"message": "Worker 已启动", "status": worker.status.value}

    elif action == "stop":
        await worker.stop()
        return {"message": "Worker 已停止", "status": worker.status.value}

    elif action == "pause":
        await worker.pause()
        return {"message": "Worker 已暂停", "status": worker.status.value}

    elif action == "resume":
        await worker.resume()
        return {"message": "Worker 已恢复", "status": worker.status.value}

    else:
        raise HTTPException(status_code=400, detail=f"未知操作: {action}")


@router.get("/status")
async def get_worker_status(
    db: Session = Depends(get_db)
):
    """获取 Worker 当前状态"""
    return worker.get_status()


@router.post("/reset-stats")
async def reset_daily_stats(
    db: Session = Depends(get_db)
):
    """重置每日统计"""
    worker.reset_daily_stats()
    return {"message": "每日统计已重置"}


# ============== 任务队列 API ==============

@router.post("/queue/add")
async def add_to_queue(
    request: QueueAddRequest,
    db: Session = Depends(get_db)
):
    """添加章节到写作队列"""
    service = TaskQueueService(db)
    result = service.add_chapters_to_queue(
        project_id=request.project_id,
        chapter_ids=request.chapter_ids
    )
    return result


@router.get("/queue/status")
async def get_queue_status(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """获取队列状态"""
    service = TaskQueueService(db)
    return service.get_queue_status(project_id=project_id)


@router.delete("/queue/{chapter_id}")
async def remove_from_queue(
    chapter_id: int,
    db: Session = Depends(get_db)
):
    """从队列中移除章节"""
    service = TaskQueueService(db)
    success = service.remove_from_queue(chapter_id)

    if not success:
        raise HTTPException(status_code=400, detail="无法移除章节")

    return {"message": f"章节 {chapter_id} 已从队列移除"}


@router.post("/queue/reorder")
async def reorder_queue(
    request: QueueReorderRequest,
    db: Session = Depends(get_db)
):
    """重新排序队列"""
    service = TaskQueueService(db)
    success = service.reorder_queue(request.task_ids)

    if not success:
        raise HTTPException(status_code=400, detail="重新排序失败")

    return {"message": "队列已重新排序"}


@router.post("/queue/clear-failed")
async def clear_failed(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """清空失败的章节，重置为 pending"""
    service = TaskQueueService(db)
    count = service.clear_failed(project_id)
    return {"message": f"已重置 {count} 个失败的章节"}


# ============== 写作计划 API ==============

@router.get("/plan/{project_id}")
async def get_writing_plan(
    project_id: int,
    db: Session = Depends(get_db)
):
    """获取写作计划"""
    service = TaskQueueService(db)
    plan = service.get_writing_plan(project_id)

    if "error" in plan:
        raise HTTPException(status_code=404, detail=plan["error"])

    return plan


# ============== 24小时循环配置 API ==============

@router.get("/config")
async def get_worker_config():
    """获取 Worker 配置"""
    return {
        "check_interval": 5,  # 秒
        "default_daily_word_goal": 10000,
        "default_daily_token_budget": 100000,
        "auto_start_next": True,  # 自动开始下一章
        "max_retries": 3,  # 失败重试次数
    }


@router.get("/stats")
async def get_worker_stats(
    db: Session = Depends(get_db)
):
    """获取详细统计信息"""
    queue_status = {}
    stats_error = None
    try:
        service = TaskQueueService(db)
        queue_status = service.get_queue_status()
    except Exception as e:
        stats_error = {"type": "QueueStatsError", "message": str(e)}

    return {
        "worker": worker.get_status(),
        "queue": queue_status or None,
        "overall_progress": queue_status.get("progress", {}) if queue_status else {},
        "error": stats_error,
    }

@router.get("/health")
async def get_worker_health():
    """Worker 健康诊断——独立于 stats，不因队列统计异常而失败"""
    ws = worker.get_status()
    db_ok = True
    warnings = []
    try:
        from app.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        db_ok = False
        warnings.append(f"数据库异常: {e}")
    return {
        "ok": db_ok,
        "worker_status": ws.get("status", "unknown"),
        "queue_service_ok": True,
        "db_ok": db_ok,
        "pending_tasks": ws.get("pending_tasks", 0) or 0,
        "running_tasks": ws.get("running_tasks", 0) or 0,
        "failed_tasks": ws.get("failed_tasks", 0) or 0,
        "warnings": warnings,
    }
