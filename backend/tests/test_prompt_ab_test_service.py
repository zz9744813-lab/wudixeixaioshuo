"""
PromptABTestService 单元测试 (P6)
验证真实 A/B：候选未超阈值不上线，超阈值才上线，且实验记录落库。
"""

import asyncio

from sqlalchemy.orm import Session

import app.services.prompt_ab_test_service as ab_module
from app.models.evolution import PromptABTestRun
from app.services.prompt_ab_test_service import PromptABTestService


_SAMPLES = [
    {"id": 1, "content": "样本正文一" * 50, "score": 70},
    {"id": 2, "content": "样本正文二" * 50, "score": 72},
    {"id": 3, "content": "样本正文三" * 50, "score": 68},
]


class _FakeLLM:
    """根据 prompt 内容返回不同分数：候选含"强力"返回高分，否则低分。"""

    async def generate(self, prompt, **kwargs):
        score = 88 if "强力" in prompt else 70
        return {
            "content": '{"overall_score": %d}' % score,
            "cost": 0.001,
            "total_tokens": 10,
        }


def test_candidate_passes_threshold(db_session, monkeypatch):
    monkeypatch.setattr(ab_module, "llm_manager", _FakeLLM())
    service = PromptABTestService(db_session)

    result = asyncio.run(service.run_ab_test(
        project_id=1,
        role="critic",
        baseline_prompt="普通审稿",
        candidate_prompts=[{"prompt": "强力审稿提示词"}],
        samples=_SAMPLES,
        min_improvement=3.0,
    ))

    assert result["winner"] is not None
    assert result["winner"]["passed"] is True
    assert result["winner"]["improvement"] >= 3.0

    rows = db_session.query(PromptABTestRun).all()
    assert len(rows) == 1
    assert rows[0].passed == 1


def test_candidate_below_threshold_rejected(db_session, monkeypatch):
    monkeypatch.setattr(ab_module, "llm_manager", _FakeLLM())
    service = PromptABTestService(db_session)

    result = asyncio.run(service.run_ab_test(
        project_id=1,
        role="critic",
        baseline_prompt="普通审稿",
        candidate_prompts=[{"prompt": "另一个普通审稿"}],  # 不含"强力"，分数相同
        samples=_SAMPLES,
        min_improvement=3.0,
    ))

    assert result["winner"] is None
    rows = db_session.query(PromptABTestRun).all()
    assert len(rows) == 1
    assert rows[0].passed == 0
    assert rows[0].decision == "reject"


def test_insufficient_samples_skips(db_session, monkeypatch):
    monkeypatch.setattr(ab_module, "llm_manager", _FakeLLM())
    service = PromptABTestService(db_session)

    result = asyncio.run(service.run_ab_test(
        project_id=1,
        role="critic",
        baseline_prompt="普通审稿",
        candidate_prompts=[{"prompt": "强力审稿"}],
        samples=_SAMPLES[:2],  # 仅2个，不足 min_samples=3
        min_improvement=3.0,
    ))
    assert result["winner"] is None
    assert "样本不足" in result.get("reason", "")
