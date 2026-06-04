"""
Agent Model Configs API - 模型配置聚合 API (Phase 1)

端点:
- GET  /api/agent-model-configs                  列出所有 Agent 卡片
- GET  /api/agent-model-configs/{role}           单个 Agent 详情
- PUT  /api/agent-model-configs/{role}/binding  更新绑定 (auto/manual)
- POST /api/agent-model-configs/routing-preview dry-run 调度
- POST /api/agent-model-configs/auto-assign     一键自动分配
- GET  /api/agent-model-configs/{role}/routing-events 历史决策
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps.auth import require_api_key
from app.services.agent_model_config_service import (
    AgentModelConfigService,
    CATEGORY_MAP,
    CATEGORY_TITLES,
    ROLE_DESCRIPTIONS,
)
from app.services.openai_llm_service import LLMServiceManager

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------- Schemas ----------

class BindingUpdate(BaseModel):
    """更新单个 Agent 绑定配置"""
    model_config = ConfigDict(from_attributes=True)

    assignment_mode: Optional[str] = Field(None, pattern="^(auto|manual)$")
    allowed_provider_ids: Optional[List[int]] = None
    preferred_quality: Optional[str] = Field(
        None, pattern="^(cheap|fast|balanced|quality|long_context)$"
    )
    max_cost_per_million: Optional[float] = None
    min_context_tokens: Optional[int] = None
    require_json: Optional[bool] = None
    fallback_enabled: Optional[bool] = None
    updated_by: Optional[str] = Field(None, pattern="^(user|system|migration)$")


class RoutingPreviewRequest(BaseModel):
    """路由预览请求"""
    model_config = ConfigDict(from_attributes=True)

    role: str
    allowed_provider_ids: Optional[List[int]] = None
    preferred_quality: Optional[str] = None
    require_json: Optional[bool] = None


class AutoAssignRequest(BaseModel):
    """一键自动分配请求"""
    model_config = ConfigDict(from_attributes=True)

    include_manual_locked: bool = False
    dry_run: bool = False


# ---------- Endpoints ----------

@router.get("")
async def list_agent_cards(db: Session = Depends(get_db)):
    """列出所有 Agent 卡片（页面主表格用）"""
    service = AgentModelConfigService(db)
    return service.list_agent_cards()


@router.get("/{role}")
async def get_agent_card(role: str, db: Session = Depends(get_db)):
    """获取单个 Agent 详情（含候选+历史）"""
    if role not in LLMServiceManager.SUPPORTED_ROLES:
        raise HTTPException(status_code=404, detail=f"未知角色: {role}")
    service = AgentModelConfigService(db)
    card = service.get_agent_card(role)
    if not card:
        raise HTTPException(status_code=404, detail=f"角色 {role} 无数据")
    return card


@router.put("/{role}/binding")
async def update_binding(
    role: str,
    payload: BindingUpdate,
    db: Session = Depends(get_db),
):
    """更新某个 Agent 的 binding 配置"""
    if role not in LLMServiceManager.SUPPORTED_ROLES:
        raise HTTPException(status_code=404, detail=f"未知角色: {role}")
    service = AgentModelConfigService(db)
    try:
        # 显式传 updated_by=user（除非 client 指定）
        data = payload.model_dump(exclude_unset=True)
        if "updated_by" not in data:
            data["updated_by"] = "user"
        result = service.update_binding(role, data)
        return {"ok": True, "binding": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/routing-preview")
async def routing_preview(
    payload: RoutingPreviewRequest,
    db: Session = Depends(get_db),
):
    """Dry-run 路由预览 - 不发请求"""
    if payload.role not in LLMServiceManager.SUPPORTED_ROLES:
        raise HTTPException(status_code=404, detail=f"未知角色: {payload.role}")
    service = AgentModelConfigService(db)
    override = payload.model_dump(exclude_unset=True, exclude={"role"})
    return service.routing_preview(payload.role, override)


@router.post("/auto-assign")
async def auto_assign(
    payload: AutoAssignRequest,
    db: Session = Depends(get_db),
):
    """一键自动分配 - 对所有 auto 模式的 role 跑 routing-preview 落库"""
    service = AgentModelConfigService(db)
    return service.auto_assign_all(
        include_manual=payload.include_manual_locked,
        dry_run=payload.dry_run,
    )


@router.get("/{role}/routing-events")
async def list_routing_events(
    role: str,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """单个 Agent 的调度决策历史"""
    if role not in LLMServiceManager.SUPPORTED_ROLES:
        raise HTTPException(status_code=404, detail=f"未知角色: {role}")
    from app.models.model_routing_event import ModelRoutingEvent
    from sqlalchemy import desc
    events = (
        db.query(ModelRoutingEvent)
        .filter(ModelRoutingEvent.role == role)
        .order_by(desc(ModelRoutingEvent.created_at))
        .limit(limit)
        .all()
    )
    return {
        "role": role,
        "items": [
            {
                "id": e.id,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "assignment_mode": e.assignment_mode,
                "selected_provider_id": e.selected_provider_id,
                "selected_provider_name": e.selected_provider_name,
                "selected_model_name": e.selected_model_name,
                "decision_reason": e.decision_reason,
                "fallback_used": e.fallback_used,
                "candidates": e.get_candidates(),
                "score_breakdown": e.get_score_breakdown(),
            }
            for e in events
        ],
        "total": len(events),
    }


@router.get("/meta/roles")
async def list_roles_meta(db: Session = Depends(get_db)):
    """支持的 role 列表及元信息（给前端下拉/分类用）"""
    return {
        "roles": [
            {
                "key": role,
                "name": ROLE_DESCRIPTIONS.get(role, role),
                "category": next(
                    (cat for cat, rs in CATEGORY_MAP.items() if role in rs), "other"
                ),
                "category_title": CATEGORY_TITLES.get(
                    next(
                        (cat for cat, rs in CATEGORY_MAP.items() if role in rs), "other"
                    ),
                    "其他",
                ),
            }
            for role in LLMServiceManager.SUPPORTED_ROLES
        ]
    }
