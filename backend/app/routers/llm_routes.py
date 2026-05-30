"""
LLM Routes API - LLM路由配置管理API
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps.auth import require_api_key
from app.models.provider_route_config import ProviderRouteConfig
from app.schemas.llm_router import (
    ProviderRouteConfigCreate,
    ProviderRouteConfigListResponse,
    ProviderRouteConfigResponse,
    ProviderRouteConfigUpdate,
    RoleListResponse,
    RoleRouteInfo,
    RouteStats,
    RouteStatsResponse,
    RouteTestRequest,
    RouteTestResponse,
)
from app.services.llm_router import LLMRouter, get_llm_router

router = APIRouter()


@router.get("", response_model=ProviderRouteConfigListResponse)
async def list_route_configs(
    role: Optional[str] = Query(None, description="按角色过滤"),
    provider_id: Optional[int] = Query(None, description="按provider过滤"),
    db: Session = Depends(get_db),
):
    """获取路由配置列表"""
    query = db.query(ProviderRouteConfig)

    if role:
        query = query.filter(ProviderRouteConfig.role == role)

    if provider_id:
        query = query.filter(ProviderRouteConfig.provider_id == provider_id)

    configs = query.order_by(
        ProviderRouteConfig.role,
        ProviderRouteConfig.priority,
        ProviderRouteConfig.weight.desc()
    ).all()

    items = []
    for config in configs:
        provider = config.provider
        item = ProviderRouteConfigResponse(
            id=config.id,
            provider_id=config.provider_id,
            role=config.role,
            priority=config.priority,
            weight=config.weight,
            enabled=config.enabled,
            rpm_limit=config.rpm_limit,
            tpm_limit=config.tpm_limit,
            timeout_seconds=config.timeout_seconds,
            max_retries=config.max_retries,
            provider_name=provider.name if provider else None,
            provider_type=provider.provider_type if provider else None,
            base_url=provider.base_url if provider else None,
            default_model=provider.default_model if provider else None,
            circuit_breaker_threshold=config.circuit_breaker_threshold,
            circuit_breaker_reset_seconds=config.circuit_breaker_reset_seconds,
            consecutive_failures=config.consecutive_failures,
            circuit_breaker_opened_at=config.circuit_breaker_opened_at,
            is_circuit_open=LLMRouter(db)._is_circuit_open(config),
            total_calls=config.total_calls,
            success_calls=config.success_calls,
            failed_calls=config.failed_calls,
            avg_latency_ms=config.avg_latency_ms,
            created_at=config.created_at,
            updated_at=config.updated_at,
        )
        items.append(item)

    return ProviderRouteConfigListResponse(items=items, total=len(items))


@router.post("", response_model=ProviderRouteConfigResponse)
async def create_route_config(
    config: ProviderRouteConfigCreate,
    db: Session = Depends(get_db),
):
    """创建路由配置"""
    # 检查provider是否存在
    from app.models.model_config import ModelProvider
    provider = db.query(ModelProvider).filter(ModelProvider.id == config.provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider不存在")

    # 创建配置
    db_config = ProviderRouteConfig(
        provider_id=config.provider_id,
        role=config.role,
        priority=config.priority,
        weight=config.weight,
        enabled=config.enabled,
        rpm_limit=config.rpm_limit,
        tpm_limit=config.tpm_limit,
        timeout_seconds=config.timeout_seconds,
        max_retries=config.max_retries,
    )

    db.add(db_config)
    db.commit()
    db.refresh(db_config)

    return ProviderRouteConfigResponse(
        id=db_config.id,
        provider_id=db_config.provider_id,
        role=db_config.role,
        priority=db_config.priority,
        weight=db_config.weight,
        enabled=db_config.enabled,
        rpm_limit=db_config.rpm_limit,
        tpm_limit=db_config.tpm_limit,
        timeout_seconds=db_config.timeout_seconds,
        max_retries=db_config.max_retries,
        provider_name=provider.name,
        provider_type=provider.provider_type,
        base_url=provider.base_url,
        default_model=provider.default_model,
        circuit_breaker_threshold=db_config.circuit_breaker_threshold,
        circuit_breaker_reset_seconds=db_config.circuit_breaker_reset_seconds,
        consecutive_failures=db_config.consecutive_failures,
        circuit_breaker_opened_at=db_config.circuit_breaker_opened_at,
        is_circuit_open=False,
        total_calls=db_config.total_calls,
        success_calls=db_config.success_calls,
        failed_calls=db_config.failed_calls,
        avg_latency_ms=db_config.avg_latency_ms,
        created_at=db_config.created_at,
        updated_at=db_config.updated_at,
    )


@router.get("/{config_id}", response_model=ProviderRouteConfigResponse)
async def get_route_config(
    config_id: int,
    db: Session = Depends(get_db),
):
    """获取单个路由配置"""
    config = (
        db.query(ProviderRouteConfig)
        .filter(ProviderRouteConfig.id == config_id)
        .first()
    )

    if not config:
        raise HTTPException(status_code=404, detail="路由配置不存在")

    provider = config.provider
    router = LLMRouter(db)

    return ProviderRouteConfigResponse(
        id=config.id,
        provider_id=config.provider_id,
        role=config.role,
        priority=config.priority,
        weight=config.weight,
        enabled=config.enabled,
        rpm_limit=config.rpm_limit,
        tpm_limit=config.tpm_limit,
        timeout_seconds=config.timeout_seconds,
        max_retries=config.max_retries,
        provider_name=provider.name if provider else None,
        provider_type=provider.provider_type if provider else None,
        base_url=provider.base_url if provider else None,
        default_model=provider.default_model if provider else None,
        circuit_breaker_threshold=config.circuit_breaker_threshold,
        circuit_breaker_reset_seconds=config.circuit_breaker_reset_seconds,
        consecutive_failures=config.consecutive_failures,
        circuit_breaker_opened_at=config.circuit_breaker_opened_at,
        is_circuit_open=router._is_circuit_open(config),
        total_calls=config.total_calls,
        success_calls=config.success_calls,
        failed_calls=config.failed_calls,
        avg_latency_ms=config.avg_latency_ms,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.patch("/{config_id}", response_model=ProviderRouteConfigResponse)
async def update_route_config(
    config_id: int,
    update: ProviderRouteConfigUpdate,
    db: Session = Depends(get_db),
):
    """更新路由配置"""
    config = (
        db.query(ProviderRouteConfig)
        .filter(ProviderRouteConfig.id == config_id)
        .first()
    )

    if not config:
        raise HTTPException(status_code=404, detail="路由配置不存在")

    # 更新字段
    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)

    db.commit()
    db.refresh(config)

    provider = config.provider
    router = LLMRouter(db)

    return ProviderRouteConfigResponse(
        id=config.id,
        provider_id=config.provider_id,
        role=config.role,
        priority=config.priority,
        weight=config.weight,
        enabled=config.enabled,
        rpm_limit=config.rpm_limit,
        tpm_limit=config.tpm_limit,
        timeout_seconds=config.timeout_seconds,
        max_retries=config.max_retries,
        provider_name=provider.name if provider else None,
        provider_type=provider.provider_type if provider else None,
        base_url=provider.base_url if provider else None,
        default_model=provider.default_model if provider else None,
        circuit_breaker_threshold=config.circuit_breaker_threshold,
        circuit_breaker_reset_seconds=config.circuit_breaker_reset_seconds,
        consecutive_failures=config.consecutive_failures,
        circuit_breaker_opened_at=config.circuit_breaker_opened_at,
        is_circuit_open=router._is_circuit_open(config),
        total_calls=config.total_calls,
        success_calls=config.success_calls,
        failed_calls=config.failed_calls,
        avg_latency_ms=config.avg_latency_ms,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.delete("/{config_id}")
async def delete_route_config(
    config_id: int,
    db: Session = Depends(get_db),
):
    """删除路由配置"""
    config = (
        db.query(ProviderRouteConfig)
        .filter(ProviderRouteConfig.id == config_id)
        .first()
    )

    if not config:
        raise HTTPException(status_code=404, detail="路由配置不存在")

    db.delete(config)
    db.commit()

    return {"success": True, "message": "路由配置已删除"}


@router.post("/{config_id}/reset-circuit")
async def reset_circuit_breaker(
    config_id: int,
    db: Session = Depends(get_db),
):
    """手动重置熔断器"""
    router = LLMRouter(db)
    success = router.reset_circuit_breaker(config_id)

    if not success:
        raise HTTPException(status_code=404, detail="路由配置不存在")

    return {"success": True, "message": "熔断器已重置"}


@router.post("/test", response_model=RouteTestResponse)
async def test_route(
    request: RouteTestRequest,
    db: Session = Depends(get_db),
):
    """测试路由配置"""
    router = LLMRouter(db)

    try:
        messages = [
            {"role": "user", "content": request.prompt}
        ]

        result = await router.generate(
            role=request.role,
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )

        return RouteTestResponse(
            success=True,
            role=request.role,
            provider_id=result.provider_id,
            provider_name=result.provider_name,
            model_name=result.model_name,
            content=result.content[:500] if result.content else None,  # 截断内容
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            total_tokens=result.total_tokens,
            cost=result.cost,
            duration_ms=result.duration_ms,
        )

    except Exception as e:
        return RouteTestResponse(
            success=False,
            role=request.role,
            error_message=str(e),
        )


@router.get("/stats/overview", response_model=RouteStatsResponse)
async def get_route_stats(
    role: Optional[str] = Query(None, description="按角色过滤"),
    db: Session = Depends(get_db),
):
    """获取路由统计信息"""
    router = LLMRouter(db)
    stats_data = router.get_route_stats(role)

    stats = []
    overall_total_calls = 0
    overall_total_cost = 0.0

    for data in stats_data:
        total_calls = data["total_calls"]
        success_calls = data["success_calls"]
        failed_calls = data["failed_calls"]

        success_rate = (success_calls / total_calls * 100) if total_calls > 0 else 0

        # 估算成本（从数据库查询更准确）
        from app.models.model_config import ModelCallLog
        cost_result = db.query(ModelCallLog).filter(
            ModelCallLog.role == data["role"]
        ).with_entities(
            func.sum(ModelCallLog.estimated_cost)
        ).scalar()

        total_cost = float(cost_result) if cost_result else 0.0
        overall_total_cost += total_cost
        overall_total_calls += total_calls

        stats.append(RouteStats(
            role=data["role"],
            total_calls=total_calls,
            success_calls=success_calls,
            failed_calls=failed_calls,
            success_rate=round(success_rate, 2),
            avg_latency_ms=data["avg_latency_ms"],
            total_cost=round(total_cost, 4),
            recent_failures=data["consecutive_failures"],
        ))

    return RouteStatsResponse(
        stats=stats,
        overall_total_calls=overall_total_calls,
        overall_total_cost=round(overall_total_cost, 4),
    )


@router.get("/roles/list", response_model=RoleListResponse)
async def list_roles(
    db: Session = Depends(get_db),
):
    """获取支持的角色列表及路由信息"""
    from app.services.openai_llm_service import LLMServiceManager

    roles_info = []

    for role in LLMServiceManager.SUPPORTED_ROLES:
        routes = (
            db.query(ProviderRouteConfig)
            .filter(ProviderRouteConfig.role == role)
            .all()
        )

        enabled_routes = [r for r in routes if r.enabled]
        primary = enabled_routes[0] if enabled_routes else None
        fallbacks = enabled_routes[1:] if len(enabled_routes) > 1 else []

        # 角色描述映射
        descriptions = {
            "planner": "规划Agent，负责章节规划",
            "draft": "起草Agent，负责写作内容",
            "critic": "审稿Agent，负责多维度评分",
            "rewrite": "改写Agent，负责改稿优化",
            "continuity": "连续性检查Agent，负责一致性检查",
            "learning": "学习Agent，负责拆书学习",
            "study": "学习/分析Agent",
            "split": "分章Agent",
            "analyze": "分析Agent",
            "memory_update": "记忆更新Agent",
            "memory_retrieval": "记忆检索Agent",
            "foreshadow": "伏笔管理Agent",
            "logic_critic": "逻辑评审Agent",
            "style_critic": "文风评审Agent",
            "commercial_critic": "商业性评审Agent",
            "research": "联网研究Agent",
            "meta_prompt": "Prompt生成Agent",
            "default": "默认角色",
        }

        info = RoleRouteInfo(
            role=role,
            description=descriptions.get(role, role),
            route_count=len(routes),
            enabled_route_count=len(enabled_routes),
            primary_provider=primary.provider.name if primary and primary.provider else None,
            fallback_providers=[r.provider.name for r in fallbacks if r.provider],
        )
        roles_info.append(info)

    return RoleListResponse(roles=roles_info)
