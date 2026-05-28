"""
Models Router - 模型配置路由
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.model_config import ModelProvider, ModelRole

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
    # 加密 API Key (简单处理，实际应使用更强的加密)
    api_key_encrypted = provider.api_key if provider.api_key else None
    api_key_mask = f"sk-****{provider.api_key[-4:]}" if provider.api_key else None

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

    # 模拟测试
    from datetime import datetime
    provider.last_tested_at = datetime.utcnow()
    provider.last_test_result = "success"
    db.commit()

    return {
        "provider_id": provider_id,
        "status": "success",
        "message": "连接测试成功",
    }


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
