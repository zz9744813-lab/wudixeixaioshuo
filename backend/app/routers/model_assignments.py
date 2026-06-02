"""
Model Assignments Router - Agent 模型分配（按角色独立配置）
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.model_config import ModelProvider, ModelRole
from app.models.provider_route_config import ProviderRouteConfig
from app.services.openai_llm_service import OpenAILLMService
from app.services.secret_service import decrypt_api_key

router = APIRouter()

# 所有支持的角色
SUPPORTED_ROLES = [
    "planner", "draft", "critic", "rewrite", "continuity",
    "learning", "study", "split", "analyze",
    "memory_update", "memory_retrieval", "foreshadow",
    "logic_critic", "style_critic", "commercial_critic",
    "default",
]

# 角色描述（供前端展示）
ROLE_DESCRIPTIONS = {
    "planner": "规划者 — 负责章节内容规划",
    "draft": "起草者 — 负责章节草稿生成",
    "critic": "评审者 — 负责多维度评审",
    "rewrite": "改写者 — 负责根据评审改写",
    "continuity": "一致性检查 — 负责连续性检查",
    "learning": "学习者 — 负责拆书学习",
    "study": "学习分析 — 负责学习分析",
    "split": "拆分者 — 负责文本拆分",
    "analyze": "分析者 — 负责内容分析",
    "memory_update": "记忆更新 — 负责长期记忆更新",
    "memory_retrieval": "记忆检索 — 负责记忆检索",
    "foreshadow": "伏笔管理 — 负责伏笔跟踪",
    "logic_critic": "逻辑评审 — 负责逻辑一致性检查",
    "style_critic": "风格评审 — 负责写作风格评审",
    "commercial_critic": "商业评审 — 负责商业价值评审",
    "default": "默认 — 未指定角色时的回退",
}

# 角色推荐默认值
ROLE_DEFAULTS = {
    "planner": {"temperature": 0.3, "max_tokens": 4000},
    "draft": {"temperature": 0.7, "max_tokens": 8000},
    "critic": {"temperature": 0.3, "max_tokens": 4000},
    "rewrite": {"temperature": 0.7, "max_tokens": 8000},
    "continuity": {"temperature": 0.3, "max_tokens": 4000},
    "learning": {"temperature": 0.3, "max_tokens": 4000},
    "study": {"temperature": 0.3, "max_tokens": 4000},
    "split": {"temperature": 0.3, "max_tokens": 4000},
    "analyze": {"temperature": 0.3, "max_tokens": 4000},
    "memory_update": {"temperature": 0.3, "max_tokens": 2000},
    "memory_retrieval": {"temperature": 0.1, "max_tokens": 2000},
    "foreshadow": {"temperature": 0.4, "max_tokens": 4000},
    "logic_critic": {"temperature": 0.2, "max_tokens": 4000},
    "style_critic": {"temperature": 0.3, "max_tokens": 4000},
    "commercial_critic": {"temperature": 0.3, "max_tokens": 4000},
    "default": {"temperature": 0.5, "max_tokens": 4000},
}


class RoleAssignmentUpdate(BaseModel):
    provider_id: int
    model_name: str
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    timeout_seconds: Optional[int] = None
    max_retries: Optional[int] = None


@router.get("/")
async def list_assignments(db: Session = Depends(get_db)):
    """获取所有 Agent 角色的模型分配情况"""
    # 获取所有已配置的角色（全局）
    roles = db.query(ModelRole).filter(ModelRole.project_id == None).all()
    role_map = {r.role: r for r in roles}

    # 获取所有启用的 Provider
    providers = db.query(ModelProvider).filter(ModelProvider.is_enabled == 1).all()
    provider_list = [
        {
            "id": p.id,
            "name": p.name,
            "provider_type": p.provider_type,
            "base_url": p.base_url,
            "default_model": p.default_model,
        }
        for p in providers
    ]

    # 获取所有路由配置
    route_configs = db.query(ProviderRouteConfig).all()
    route_map = {(rc.provider_id, rc.role): rc for rc in route_configs}

    # 构建分配列表
    assignments = []
    for role in SUPPORTED_ROLES:
        r = role_map.get(role)
        defaults = ROLE_DEFAULTS.get(role, {"temperature": 0.5, "max_tokens": 4000})

        assignment = {
            "role": role,
            "description": ROLE_DESCRIPTIONS.get(role, role),
            "configured": r is not None,
        }

        if r:
            assignment["id"] = r.id
            assignment["provider_id"] = r.provider_id
            assignment["model_name"] = r.model_name
            # P1-1: 数据库历史数据可能为 NULL（手工 SQL 插入时未走
            # SQLAlchemy default），用 defaults 兜底避免前端拿到 null 后
            # input 显示空白
            assignment["temperature"] = (
                r.temperature if r.temperature is not None
                else defaults["temperature"]
            )
            assignment["max_tokens"] = (
                r.max_tokens if r.max_tokens is not None
                else defaults["max_tokens"]
            )
            assignment["provider"] = {
                "id": r.provider.id,
                "name": r.provider.name,
                "provider_type": r.provider.provider_type,
                "default_model": r.provider.default_model,
            } if r.provider else None
            # 从路由配置获取超时/重试
            rc = route_map.get((r.provider_id, r.role))
            assignment["timeout_seconds"] = rc.timeout_seconds if rc else None
            assignment["max_retries"] = rc.max_retries if rc else None
        else:
            assignment["id"] = None
            assignment["provider_id"] = None
            assignment["model_name"] = None
            assignment["temperature"] = defaults["temperature"]
            assignment["max_tokens"] = defaults["max_tokens"]
            assignment["provider"] = None
            assignment["timeout_seconds"] = None
            assignment["max_retries"] = None

        assignment["defaults"] = defaults
        assignments.append(assignment)

    return {
        "assignments": assignments,
        "providers": provider_list,
        "supported_roles": SUPPORTED_ROLES,
    }


@router.put("/{role}")
async def update_assignment(role: str, update: RoleAssignmentUpdate, db: Session = Depends(get_db)):
    """更新指定 Agent 角色的模型分配（仅影响此角色，不覆盖其他角色）"""
    if role not in SUPPORTED_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的角色: {role}。支持的角色: {', '.join(SUPPORTED_ROLES)}",
        )

    # 验证 Provider 存在
    provider = db.query(ModelProvider).filter(ModelProvider.id == update.provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider 不存在")
    if provider.is_enabled != 1:
        raise HTTPException(status_code=400, detail=f"Provider '{provider.name}' 未启用")

    defaults = ROLE_DEFAULTS.get(role, {"temperature": 0.5, "max_tokens": 4000})
    temperature = update.temperature if update.temperature is not None else defaults["temperature"]
    max_tokens = update.max_tokens if update.max_tokens is not None else defaults["max_tokens"]

    # Upsert ModelRole
    existing = db.query(ModelRole).filter(
        ModelRole.role == role,
        ModelRole.project_id == None,
    ).first()

    if existing:
        existing.provider_id = update.provider_id
        existing.model_name = update.model_name
        existing.temperature = temperature
        existing.max_tokens = max_tokens
    else:
        existing = ModelRole(
            role=role,
            provider_id=update.provider_id,
            model_name=update.model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            project_id=None,
            priority=1,
        )
        db.add(existing)

    db.commit()
    db.refresh(existing)

    # 同步到 ProviderRouteConfig
    route_config = db.query(ProviderRouteConfig).filter(
        ProviderRouteConfig.provider_id == update.provider_id,
        ProviderRouteConfig.role == role,
    ).first()

    timeout = update.timeout_seconds or 60
    retries = update.max_retries or 2

    if route_config:
        route_config.timeout_seconds = timeout
        route_config.max_retries = retries
    else:
        # 如果已有旧 Provider 的路由配置，先删除
        old_routes = db.query(ProviderRouteConfig).filter(
            ProviderRouteConfig.role == role,
        ).all()
        for old_rc in old_routes:
            db.delete(old_rc)

        db.add(ProviderRouteConfig(
            provider_id=update.provider_id,
            role=role,
            priority=1,
            weight=1,
            enabled=True,
            timeout_seconds=timeout,
            max_retries=retries,
        ))

    db.commit()

    return {
        "role": existing.role,
        "provider_id": existing.provider_id,
        "model_name": existing.model_name,
        "temperature": existing.temperature,
        "max_tokens": existing.max_tokens,
        "provider": {
            "id": provider.id,
            "name": provider.name,
        },
        "message": f"角色 '{role}' 已分配模型 {existing.model_name}（Provider: {provider.name}）",
    }


@router.delete("/{role}")
async def delete_assignment(role: str, db: Session = Depends(get_db)):
    """删除指定 Agent 角色的模型分配"""
    if role not in SUPPORTED_ROLES:
        raise HTTPException(status_code=400, detail=f"不支持的角色: {role}")

    existing = db.query(ModelRole).filter(
        ModelRole.role == role,
        ModelRole.project_id == None,
    ).first()

    if not existing:
        raise HTTPException(status_code=404, detail=f"角色 '{role}' 未配置模型分配")

    # 删除关联的路由配置
    db.query(ProviderRouteConfig).filter(
        ProviderRouteConfig.role == role,
    ).delete()

    db.delete(existing)
    db.commit()

    return {"message": f"角色 '{role}' 的模型分配已删除", "role": role}


@router.post("/{role}/test")
async def test_assignment(role: str, db: Session = Depends(get_db)):
    """测试指定 Agent 角色的模型连接"""
    if role not in SUPPORTED_ROLES:
        raise HTTPException(status_code=400, detail=f"不支持的角色: {role}")

    role_config = db.query(ModelRole).filter(
        ModelRole.role == role,
        ModelRole.project_id == None,
    ).first()

    if not role_config:
        raise HTTPException(status_code=404, detail=f"角色 '{role}' 尚未配置模型")

    provider = db.query(ModelProvider).filter(ModelProvider.id == role_config.provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider 不存在")

    if not provider.api_key_encrypted:
        raise HTTPException(status_code=400, detail=f"Provider '{provider.name}' 未配置 API Key")

    try:
        api_key = decrypt_api_key(provider.api_key_encrypted)
        llm_service = OpenAILLMService(
            base_url=provider.base_url,
            api_key=api_key,
            model_name=role_config.model_name,
            timeout=provider.timeout_seconds or 120,
            retry_times=1,
        )

        test_response = await llm_service.generate(
            prompt=f"你好，这是对 '{role}' 代理角色的连接测试，请回复 OK。",
            max_tokens=20,
            temperature=0.0,
        )

        await llm_service.close()

        return {
            "role": role,
            "provider_id": provider.id,
            "provider_name": provider.name,
            "model_name": role_config.model_name,
            "status": "success",
            "message": f"角色 '{role}' 连接测试成功",
            "response_preview": (test_response.get("content") or "")[:100],
            "model_used": test_response.get("model"),
            "tokens": test_response.get("total_tokens"),
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={
                "role": role,
                "provider_id": provider.id,
                "provider_name": provider.name,
                "model_name": role_config.model_name,
                "status": "failed",
                "message": f"角色 '{role}' 连接测试失败: {str(e)}",
            },
        )