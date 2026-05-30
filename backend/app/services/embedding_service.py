"""
EmbeddingService - 文本向量化服务 (P4)
复用模型配置中心的 provider 配置，调用 OpenAI 兼容的 /embeddings 接口。
未配置或失败时返回空向量，绝不抛出以阻断主流程。
"""

import logging
from typing import List, Optional

import httpx
from sqlalchemy.orm import Session

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """文本向量化服务"""

    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self.model_name = settings.EMBEDDING_MODEL
        self.dim = settings.EMBEDDING_DIM

    def _resolve_provider(self):
        """从模型配置中心解析 embedding provider（base_url / api_key / model）。

        优先使用 role='embedding' 的映射，否则回退默认 provider。
        返回 (base_url, api_key, model_name) 或 None。
        """
        if not self.db:
            return None
        try:
            from app.models.model_config import ModelProvider, ModelRole
            from app.services.secret_service import decrypt_api_key

            providers = self.db.query(ModelProvider).filter(
                ModelProvider.is_enabled == 1
            ).all()
            if not providers:
                return None

            role = self.db.query(ModelRole).filter(
                ModelRole.role == "embedding",
                ModelRole.provider_id.in_([p.id for p in providers]),
            ).first()

            if role and role.provider:
                provider = role.provider
                model = role.model_name or self.model_name
            else:
                provider = next((p for p in providers if p.is_default == 1), providers[0])
                model = self.model_name

            return (
                provider.base_url.rstrip("/"),
                decrypt_api_key(provider.api_key_encrypted),
                model,
            )
        except Exception as e:
            logger.warning(f"解析 embedding provider 失败: {e}")
            return None

    async def embed_text(self, text: str, model_name: Optional[str] = None) -> List[float]:
        result = await self.embed_texts([text], model_name=model_name)
        return result[0] if result else []

    async def embed_texts(
        self, texts: List[str], model_name: Optional[str] = None
    ) -> List[List[float]]:
        if not texts:
            return []

        resolved = self._resolve_provider()
        if not resolved:
            logger.warning("未配置 embedding provider，返回空向量")
            return [[] for _ in texts]

        base_url, api_key, model = resolved
        model = model_name or model

        payload = {"model": model, "input": texts}
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(base_url=base_url, timeout=httpx.Timeout(60)) as client:
                resp = await client.post("/embeddings", json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
            items = sorted(data.get("data", []), key=lambda x: x.get("index", 0))
            return [item.get("embedding", []) for item in items]
        except Exception as e:
            logger.warning(f"embedding 调用失败: {e}")
            return [[] for _ in texts]
