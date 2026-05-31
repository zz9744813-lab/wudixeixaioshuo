"""
Models Router - 模型配置路由
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.model_config import ModelProvider, ModelRole
from app.services.openai_llm_service import OpenAILLMService
from app.services.secret_service import encrypt_api_key, decrypt_api_key, mask_api_key
from app.utils.time_utils import utc_now

router = APIRouter()


# Pydantic 模型
class ProviderCreate(BaseModel):
    name: str
    provider_type: str = Field(..., pattern="^(openai|anthropic|gemini|openrouter|custom)$")
    base_url: str
    api_key: Optional[str] = None
    default_model: str = "gpt-3.5-turbo"
    is_enabled: bool = True


class ProviderResponse(BaseModel):
    id: int
    name: str
    provider_type: str
    base_url: str
    default_model: str
    is_enabled: bool
    last_test_result: Optional[str]

    class Config:
        from_attributes = True


@router.get("/providers", response_model=List[ProviderResponse])
async def list_providers(db: Session = Depends(get_db)):
    """获取模型提供商列表"""
    providers = db.query(ModelProvider).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "provider_type": p.provider_type,
            "base_url": p.base_url,
            "default_model": p.default_model,
            "is_enabled": p.is_enabled == 1,
            "last_test_result": p.last_test_result,
        }
        for p in providers
    ]


@router.post("/providers")
async def create_provider(provider: ProviderCreate, db: Session = Depends(get_db)):
    """创建模型提供商"""
    # 加密 API Key
    api_key_encrypted = encrypt_api_key(provider.api_key) if provider.api_key else None
    api_key_mask = mask_api_key(provider.api_key)

    db_provider = ModelProvider(
        name=provider.name,
        provider_type=provider.provider_type,
        base_url=provider.base_url,
        api_key_encrypted=api_key_encrypted,
        api_key_mask=api_key_mask,
        default_model=provider.default_model,
        is_enabled=1 if provider.is_enabled else 0,
    )
    db.add(db_provider)
    db.commit()
    db.refresh(db_provider)

    return {
        "id": db_provider.id,
        "name": db_provider.name,
        "message": "提供商已创建",
    }


class ProviderUpdate(BaseModel):
    name: Optional[str] = None
    provider_type: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    default_model: Optional[str] = None
    is_enabled: Optional[bool] = None

@router.put("/providers/{provider_id}")
async def update_provider(provider_id: int, provider: ProviderUpdate, db: Session = Depends(get_db)):
    """更新模型提供商配置"""
    db_provider = db.query(ModelProvider).filter(ModelProvider.id == provider_id).first()
    if not db_provider:
        raise HTTPException(status_code=404, detail="Provider 不存在")

    update_data = provider.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "api_key" and value:
            db_provider.api_key_encrypted = encrypt_api_key(value)
            db_provider.api_key_mask = mask_api_key(value)
        elif hasattr(db_provider, field):
            setattr(db_provider, field, value)

    db_provider.updated_at = utc_now()
    db.commit()
    db.refresh(db_provider)

    return {
        "id": db_provider.id,
        "name": db_provider.name,
        "provider_type": db_provider.provider_type,
        "base_url": db_provider.base_url,
        "default_model": db_provider.default_model,
        "is_enabled": db_provider.is_enabled == 1,
        "last_test_result": db_provider.last_test_result,
        "message": "Provider 已更新",
    }

@router.get("/providers/{provider_id}")
async def get_provider(provider_id: int, db: Session = Depends(get_db)):
    """获取提供商详情"""
    provider = db.query(ModelProvider).filter(ModelProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="提供商不存在")

    return {
        "id": provider.id,
        "name": provider.name,
        "provider_type": provider.provider_type,
        "base_url": provider.base_url,
        "api_key_mask": provider.api_key_mask,
        "default_model": provider.default_model,
        "is_enabled": provider.is_enabled == 1,
        "default_temperature": provider.default_temperature,
        "default_max_tokens": provider.default_max_tokens,
        "timeout_seconds": provider.timeout_seconds,
        "retry_times": provider.retry_times,
        "last_test_result": provider.last_test_result,
        "last_tested_at": provider.last_tested_at.isoformat() if provider.last_tested_at else None,
    }


@router.post("/providers/{provider_id}/test")
async def test_provider(provider_id: int, db: Session = Depends(get_db)):
    """测试提供商连接"""
    provider = db.query(ModelProvider).filter(ModelProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="提供商不存在")

    try:
        # 创建临时服务实例进行测试
        llm_service = OpenAILLMService(
            base_url=provider.base_url,
            api_key=decrypt_api_key(provider.api_key_encrypted),
            model_name=provider.default_model,
            timeout=provider.timeout_seconds or 120,
            retry_times=1,  # 测试时只重试1次
        )

        # 执行健康检查
        health_result = await llm_service.health_check()

        # 尝试发送一个简单的测试请求
        test_response = await llm_service.generate(
            prompt="Hello, this is a test message. Please respond with 'OK'.",
            max_tokens=10,
            temperature=0.0,
        )

        # 更新提供商状态
        from datetime import datetime
        provider.last_tested_at = utc_now()
        provider.last_test_result = "success"
        db.commit()

        await llm_service.close()

        return {
            "provider_id": provider_id,
            "status": "success",
            "message": "连接测试成功",
            "health_check": health_result,
            "test_response": {
                "model": test_response.get("model"),
                "content_preview": test_response.get("content", "")[:50] + "..." if len(test_response.get("content", "")) > 50 else test_response.get("content", ""),
                "tokens": test_response.get("total_tokens"),
                "cost": test_response.get("cost"),
            }
        }

    except Exception as e:
        from datetime import datetime
        provider.last_tested_at = utc_now()
        provider.last_test_result = "failed"
        db.commit()

        raise HTTPException(
            status_code=400,
            detail={
                "provider_id": provider_id,
                "status": "failed",
                "message": f"连接测试失败: {str(e)}",
            }
        )


@router.delete("/providers/{provider_id}")
async def delete_provider(provider_id: int, db: Session = Depends(get_db)):
    """删除提供商"""
    provider = db.query(ModelProvider).filter(ModelProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="提供商不存在")

    db.delete(provider)
    db.commit()

    return {"message": "提供商已删除", "id": provider_id}


@router.get("/roles")
async def list_roles(project_id: Optional[int] = None, db: Session = Depends(get_db)):
    """获取角色映射列表"""
    query = db.query(ModelRole)
    if project_id:
        query = query.filter((ModelRole.project_id == project_id) | (ModelRole.project_id == None))

    roles = query.all()
    return [
        {
            "id": r.id,
            "project_id": r.project_id,
            "role": r.role,
            "model_name": r.model_name,
            "temperature": r.temperature,
            "max_tokens": r.max_tokens,
            "provider": {
                "id": r.provider.id,
                "name": r.provider.name,
            } if r.provider else None,
        }
        for r in roles
    ]


# 角色映射创建模型
class RoleCreate(BaseModel):
    role: str = Field(..., pattern="^(planner|draft|critic|rewrite|continuity|learning|study|split|analyze|memory_update|memory_retrieval|foreshadow|logic_critic|style_critic|commercial_critic|default)$")
    model_name: str
    provider_id: int
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 4000
    project_id: Optional[int] = None


class QuickSetupRequest(BaseModel):
    name: str = "默认配置"
    provider_type: str = Field(..., pattern="^(openai|anthropic|gemini|openrouter|custom)$")
    base_url: str
    api_key: str
    default_model: str = "gpt-3.5-turbo"


@router.post("/quick-setup")
async def quick_setup(config: QuickSetupRequest, db: Session = Depends(get_db)):
  """
  快速配置 LLM
  一键创建提供商并为所有角色配置默认模型（upsert 模式）
  """
  api_key_encrypted = encrypt_api_key(config.api_key)
  api_key_mask = mask_api_key(config.api_key)

  # P0-4: Upsert – 按 name + provider_type + base_url 查找已有 Provider
  existing_provider = db.query(ModelProvider).filter(
    ModelProvider.name == config.name,
    ModelProvider.provider_type == config.provider_type,
    ModelProvider.base_url == config.base_url,
  ).first()

  if existing_provider:
    # 更新已有 Provider
    existing_provider.api_key_encrypted = api_key_encrypted
    existing_provider.api_key_mask = api_key_mask
    existing_provider.default_model = config.default_model
    existing_provider.is_enabled = 1
    existing_provider.is_default = 1
    # 清除其他 Provider 的 is_default
    db.query(ModelProvider).filter(
      ModelProvider.id != existing_provider.id
    ).update({"is_default": 0})
    provider = existing_provider
  else:
    # 新建 Provider
    provider = ModelProvider(
      name=config.name,
      provider_type=config.provider_type,
      base_url=config.base_url,
      api_key_encrypted=api_key_encrypted,
      api_key_mask=api_key_mask,
      default_model=config.default_model,
      is_enabled=1,
      is_default=1,
    )
    db.add(provider)
  db.commit()
  db.refresh(provider)

  # 角色映射 (upsert)
  roles_list = [
    "planner", "draft", "critic", "rewrite", "continuity",
    "learning", "study", "split", "analyze", "default",
    "memory_update", "memory_retrieval", "foreshadow",
    "logic_critic", "style_critic", "commercial_critic",
  ]

  configured_roles = []
  for role in roles_list:
    existing = db.query(ModelRole).filter(
      ModelRole.role == role,
      ModelRole.project_id == None,
    ).first()

    if existing:
      existing.provider_id = provider.id
      existing.model_name = config.default_model
    else:
      role_config = ModelRole(
        role=role,
        provider_id=provider.id,
        model_name=config.default_model,
        temperature=0.7 if role in ["draft", "rewrite"] else 0.3,
        max_tokens=4000,
        priority=1,
      )
      db.add(role_config)
      configured_roles.append(role)

  db.commit()

  return {
    "message": "LLM 配置成功",
    "provider_id": provider.id,
    "provider_name": provider.name,
    "model": config.default_model,
    "roles_configured": roles_list,
  }
@router.post("/roles")
async def create_role(role: RoleCreate, db: Session = Depends(get_db)):
    """创建角色映射"""
    # 验证提供商存在
    provider = db.query(ModelProvider).filter(ModelProvider.id == role.provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="提供商不存在")

    # 检查是否已存在相同角色配置
    existing = db.query(ModelRole).filter(
        ModelRole.role == role.role,
        ModelRole.project_id == role.project_id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail=f"角色 '{role.role}' 的配置已存在")

    role_config = ModelRole(
        role=role.role,
        provider_id=role.provider_id,
        model_name=role.model_name,
        temperature=role.temperature,
        max_tokens=role.max_tokens,
        project_id=role.project_id,
        priority=1,
    )
    db.add(role_config)
    db.commit()
    db.refresh(role_config)

    return {
        "id": role_config.id,
        "role": role_config.role,
        "model_name": role_config.model_name,
        "provider_id": role_config.provider_id,
        "message": "角色映射已创建",
    }
"""
@app:routers models.py 已完成 P0-3 模型自动发现端点
"""

# P0-3: 模型自动发现
class ModelDiscoverRequest(BaseModel):
  provider_type: str = Field(..., pattern="^(openai|anthropic|gemini|openrouter|custom)$")
  base_url: str
  api_key: str

@router.post("/discover")
async def discover_models(req: ModelDiscoverRequest):
  """临时发现模型列表 – 不保存数据库"""
  try:
    import httpx

    if req.provider_type in ("openai", "openrouter", "custom"):
      url = req.base_url.rstrip("/") + "/models"
      headers = {"Authorization": f"Bearer {req.api_key}"}
      async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()

      models = []
      for m in data.get("data", []):
        models.append({
          "id": m.get("id", ""),
          "name": m.get("id", ""),
          "owned_by": m.get("owned_by", ""),
        })

      return {
        "ok": True,
        "provider_type": req.provider_type,
        "base_url": req.base_url,
        "count": len(models),
        "models": models,
      }

    elif req.provider_type == "anthropic":
      return {
        "ok": True,
        "provider_type": req.provider_type,
        "base_url": req.base_url,
        "count": 0,
        "models": [],
        "note": "Anthropic 暂不支持自动拉取模型列表，请手动填写模型名",
      }

    elif req.provider_type == "gemini":
      return {
        "ok": True,
        "provider_type": req.provider_type,
        "base_url": req.base_url,
        "count": 0,
        "models": [],
        "note": "Gemini 暂不支持自动拉取模型列表，请手动填写模型名",
      }

  except Exception as e:
    return {
      "ok": False,
      "error": {
        "type": "ModelDiscoveryError",
        "message": f"无法拉取模型列表：{str(e)}",
      },
    }


@router.get("/providers/{provider_id}/models")
async def get_provider_models(provider_id: int, db: Session = Depends(get_db)):
  """读取已保存 Provider 的模型列表"""
  from app.services.secret_service import decrypt_api_key
  provider = db.query(ModelProvider).filter(ModelProvider.id == provider_id).first()
  if not provider:
    raise HTTPException(status_code=404, detail="Provider 不存在")

  try:
    import httpx
    url = provider.base_url.rstrip("/") + "/models"
    api_key = decrypt_api_key(provider.api_key_encrypted)
    headers = {"Authorization": f"Bearer {api_key}"}

    async with httpx.AsyncClient(timeout=30) as client:
      resp = await client.get(url, headers=headers)
      resp.raise_for_status()
      data = resp.json()

    models = []
    for m in data.get("data", []):
      models.append({
        "id": m.get("id", ""),
        "name": m.get("id", ""),
        "owned_by": m.get("owned_by", ""),
      })

    return {
      "ok": True,
      "provider_id": provider_id,
      "provider_name": provider.name,
      "count": len(models),
      "models": models,
    }

  except Exception as e:
    return {
      "ok": False,
      "error": {
        "type": "ModelFetchError",
        "message": f"无法获取模型列表：{str(e)}",
      },
    }


@router.post("/providers/{provider_id}/refresh-models")
async def refresh_provider_models(provider_id: int, db: Session = Depends(get_db)):
  """刷新模型列表缓存"""
  from app.services.secret_service import decrypt_api_key
  provider = db.query(ModelProvider).filter(ModelProvider.id == provider_id).first()
  if not provider:
    raise HTTPException(status_code=404, detail="Provider 不存在")

  try:
    import httpx
    url = provider.base_url.rstrip("/") + "/models"
    api_key = decrypt_api_key(provider.api_key_encrypted)
    headers = {"Authorization": f"Bearer {api_key}"}

    async with httpx.AsyncClient(timeout=30) as client:
      resp = await client.get(url, headers=headers)
      resp.raise_for_status()
      data = resp.json()

    models = []
    for m in data.get("data", []):
      models.append({
        "id": m.get("id", ""),
        "name": m.get("id", ""),
        "owned_by": m.get("owned_by", ""),
      })

    provider.last_models_refresh = utc_now()
    db.commit()

    return {
      "ok": True,
      "provider_id": provider_id,
      "count": len(models),
      "models": models,
      "refreshed_at": provider.last_models_refresh.isoformat() if provider.last_models_refresh else None,
    }

  except Exception as e:
    return {
      "ok": False,
      "error": {
        "type": "ModelRefreshError",
        "message": f"刷新失败：{str(e)}",
      },
    }
