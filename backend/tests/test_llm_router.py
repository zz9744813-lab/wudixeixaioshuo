import pytest
from sqlalchemy.orm import Session

from app.models.model_config import ModelProvider
from app.models.provider_route_config import ProviderRouteConfig
from app.services.llm_router import LLMRouter


@pytest.mark.asyncio
async def test_llm_router_uses_provider_default_model(db_session: Session, monkeypatch):
    provider = ModelProvider(
        name="测试 Provider",
        provider_type="openai",
        base_url="https://example.com/v1",
        api_key_encrypted="test-key",
        default_model="test-model",
        default_temperature=0.3,
        default_max_tokens=100,
    )
    db_session.add(provider)
    db_session.commit()

    route = ProviderRouteConfig(
        provider_id=provider.id,
        role="planner",
        priority=1,
        weight=1,
        enabled=True,
    )
    db_session.add(route)
    db_session.commit()

    monkeypatch.setattr("app.services.llm_router.decrypt_api_key", lambda value: "plain-key")

    class FakeService:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        async def generate(self, **kwargs):
            return {
                "content": "ok",
                "model": kwargs["model"],
                "input_tokens": 1,
                "output_tokens": 2,
                "total_tokens": 3,
                "cost": 0.01,
            }

        async def close(self):
            return None

    monkeypatch.setattr("app.services.llm_router.OpenAILLMService", FakeService)

    result = await LLMRouter(db_session).generate(
        role="planner",
        messages=[{"role": "user", "content": "规划"}],
    )

    assert result.content == "ok"
    assert result.model_name == "test-model"
    assert result.total_tokens == 3

    db_session.refresh(route)
    assert route.total_calls == 1
    assert route.success_calls == 1
