"""
Health Router - 健康检查路由
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter()


@router.get("/")
async def health_check(db: Session = Depends(get_db)):
    """健康检查端点"""
    try:
        # 测试数据库连接
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "service": "24小时小说 Agent 工作台",
        "version": "0.1.0",
        "database": db_status,
    }
