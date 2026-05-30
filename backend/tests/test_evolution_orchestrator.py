import pytest
from sqlalchemy.orm import Session

from app.models.evolution_auto import (
    PromptEvolutionPolicy,
    PromptEvolutionRun,
    PromptEvolutionRunStatus,
)
from app.services.evolution_orchestrator import EvolutionOrchestrator
from app.services.quality_monitor_service import QualityMonitorService


def test_quality_monitor_should_not_trigger_without_samples(db_session: Session):
    """测试无样本时不触发进化。"""
    policy = PromptEvolutionPolicy(
        role="draft",
        enabled=True,
        min_sample_count=20,
        min_average_score=80.0,
    )
    db_session.add(policy)
    db_session.commit()

    monitor = QualityMonitorService(db_session)
    assert monitor.should_trigger_evolution(policy) is False


def test_quality_monitor_collect_failure_samples(db_session: Session):
    """测试收集失败样本。"""
    monitor = QualityMonitorService(db_session)
    samples = monitor.collect_failure_samples("draft", window_days=7)
    assert isinstance(samples, list)


def test_quality_monitor_diagnose():
    """测试诊断功能。"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.database import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    monitor = QualityMonitorService(db)

    # 无样本诊断
    result = monitor.diagnose("draft", [])
    assert "暂无低分样本" in result

    # 有样本诊断
    samples = [
        {"score": 50, "chapter_id": 1},
        {"score": 60, "chapter_id": 2},
    ]
    result = monitor.diagnose("draft", samples)
    assert "质量偏低" in result or "质量严重不足" in result


def test_quality_monitor_get_quality_metrics(db_session: Session):
    """测试质量指标获取。"""
    monitor = QualityMonitorService(db_session)
    metrics = monitor.get_quality_metrics("draft")

    assert "average_score" in metrics
    assert "total_reviews" in metrics
    assert "below_80_count" in metrics


@pytest.mark.asyncio
async def test_evolution_orchestrator_run_without_policy(db_session: Session):
    """测试策略不存在时的错误处理。"""
    orchestrator = EvolutionOrchestrator(db_session)
    with pytest.raises(ValueError, match="进化策略不存在"):
        await orchestrator.run_auto_evolution(999)


@pytest.mark.asyncio
async def test_evolution_orchestrator_rollback_without_applied(db_session: Session):
    """测试回滚未应用的运行。"""
    policy = PromptEvolutionPolicy(
        role="draft",
        enabled=True,
        min_sample_count=0,
        min_average_score=100,
    )
    db_session.add(policy)
    db_session.commit()

    run = PromptEvolutionRun(
        policy_id=policy.id,
        role="draft",
        status=PromptEvolutionRunStatus.PENDING,
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    orchestrator = EvolutionOrchestrator(db_session)
    with pytest.raises(ValueError, match="只能回滚已应用的运行"):
        await orchestrator.rollback(run.id)


def test_evolution_policy_create_and_list(db_session: Session):
    """测试进化策略创建和列表。"""
    policy = PromptEvolutionPolicy(
        role="critic",
        enabled=True,
        min_sample_count=15,
        min_average_score=75.0,
        candidate_count=2,
    )
    db_session.add(policy)
    db_session.commit()
    db_session.refresh(policy)

    assert policy.id is not None
    assert policy.role == "critic"

    policies = db_session.query(PromptEvolutionPolicy).filter(
        PromptEvolutionPolicy.role == "critic"
    ).all()
    assert len(policies) >= 1
