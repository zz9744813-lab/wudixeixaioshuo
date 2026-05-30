"""Research Router - 联网研究 Agent API。"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.research import KnowledgePattern, ReaderInsight, ResearchRun, TrendReport
from app.schemas.research import (
    ApplyToProjectRequest,
    CreateResearchRunRequest,
    KnowledgePatternResponse,
    ReaderInsightResponse,
    ResearchRunResponse,
    TrendReportResponse,
)
from app.services.research_agent_service import ResearchAgentService

router = APIRouter(prefix="/research", tags=["research"])


@router.post("/runs", response_model=ResearchRunResponse)
async def create_research_run(request: CreateResearchRunRequest, db: Session = Depends(get_db)):
    """创建并执行联网研究。"""
    service = ResearchAgentService(db)
    run = await service.run_research(
        topic=request.topic,
        research_type=request.research_type,
        project_id=request.project_id,
        run_id=request.run_id,
    )
    return run


@router.get("/runs", response_model=List[ResearchRunResponse])
async def list_research_runs(
    project_id: Optional[int] = Query(None),
    research_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """获取研究运行列表。"""
    query = db.query(ResearchRun)
    if project_id:
        query = query.filter(ResearchRun.project_id == project_id)
    if research_type:
        query = query.filter(ResearchRun.research_type == research_type)
    if status:
        query = query.filter(ResearchRun.status == status)
    runs = query.order_by(ResearchRun.created_at.desc()).limit(limit).all()
    return runs


@router.get("/runs/{run_id}", response_model=ResearchRunResponse)
async def get_research_run(run_id: int, db: Session = Depends(get_db)):
    """获取研究运行详情。"""
    run = db.query(ResearchRun).filter(ResearchRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="研究运行不存在")
    return run


@router.post("/runs/{run_id}/cancel")
async def cancel_research_run(run_id: int, db: Session = Depends(get_db)):
    """取消研究运行。"""
    run = db.query(ResearchRun).filter(ResearchRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="研究运行不存在")
    if run.status in ["succeeded", "failed", "cancelled"]:
        raise HTTPException(status_code=400, detail="运行已结束，无法取消")
    run.status = "cancelled"
    db.commit()
    return {"message": "研究运行已取消", "run_id": run_id}


@router.get("/patterns", response_model=List[KnowledgePatternResponse])
async def list_knowledge_patterns(
    genre: Optional[str] = Query(None),
    pattern_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """获取知识模式列表。"""
    query = db.query(KnowledgePattern)
    if genre:
        query = query.filter(KnowledgePattern.genre == genre)
    if pattern_type:
        query = query.filter(KnowledgePattern.pattern_type == pattern_type)
    return query.order_by(KnowledgePattern.created_at.desc()).limit(limit).all()


@router.get("/reader-insights", response_model=List[ReaderInsightResponse])
async def list_reader_insights(
    genre: Optional[str] = Query(None),
    insight_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """获取读者洞察列表。"""
    query = db.query(ReaderInsight)
    if genre:
        query = query.filter(ReaderInsight.genre == genre)
    if insight_type:
        query = query.filter(ReaderInsight.insight_type == insight_type)
    return query.order_by(ReaderInsight.created_at.desc()).limit(limit).all()


@router.get("/trends", response_model=List[TrendReportResponse])
async def list_trend_reports(
    genre: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """获取趋势报告列表。"""
    query = db.query(TrendReport)
    if genre:
        query = query.filter(TrendReport.genre == genre)
    if platform:
        query = query.filter(TrendReport.platform == platform)
    return query.order_by(TrendReport.created_at.desc()).limit(limit).all()


@router.post("/apply-to-project")
async def apply_knowledge_to_project(request: ApplyToProjectRequest, db: Session = Depends(get_db)):
    """将研究知识应用到项目。"""
    service = ResearchAgentService(db)
    try:
        result = service.apply_to_project(
            knowledge_type=request.knowledge_type,
            knowledge_ids=request.knowledge_ids,
            project_id=request.project_id,
            apply_to_bible=request.apply_to_bible,
            apply_to_critic=request.apply_to_critic,
            apply_to_prompt=request.apply_to_prompt,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
