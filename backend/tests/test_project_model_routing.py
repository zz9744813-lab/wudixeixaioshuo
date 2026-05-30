"""
项目级模型路由测试 (修复"配了不生效")
验证 get_service_for 按 project_id + priority 选择模型，缺项目级配置时回退全局。
"""

from sqlalchemy.orm import Session

from app.models.model_config import ModelProvider, ModelRole
from app.services.openai_llm_service import LLMServiceManager


def _seed_provider(db_session: Session, name: str, default_model: str) -> ModelProvider:
    provider = ModelProvider(
        name=name,
        provider_type="openai",
        base_url=f"https://{name}.example.com/v1",
        api_key_encrypted=None,
        default_model=default_model,
        is_enabled=1,
    )
    db_session.add(provider)
    db_session.commit()
    return provider


def test_project_role_overrides_global(db_session: Session):
    global_p = _seed_provider(db_session, "globalp", "global-model")
    project_p = _seed_provider(db_session, "projectp", "project-model")

    # 全局 critic 配置
    db_session.add(ModelRole(
        project_id=None, provider_id=global_p.id,
        role="critic", model_name="global-critic", priority=1,
    ))
    # 项目 7 专属 critic 配置
    db_session.add(ModelRole(
        project_id=7, provider_id=project_p.id,
        role="critic", model_name="project-critic", priority=1,
    ))
    db_session.commit()

    mgr = LLMServiceManager()
    svc = mgr.get_service_for("critic", project_id=7, db=db_session)
    assert svc.model_name == "project-critic"
    assert svc.provider_name == "projectp"


def test_falls_back_to_global_when_no_project_config(db_session: Session):
    global_p = _seed_provider(db_session, "globalp2", "global-model")
    db_session.add(ModelRole(
        project_id=None, provider_id=global_p.id,
        role="draft", model_name="global-draft", priority=1,
    ))
    db_session.commit()

    mgr = LLMServiceManager()
    # 项目 99 无专属配置 → 回退全局 get_service（此处全局服务未初始化，回退 Mock）
    svc = mgr.get_service_for("draft", project_id=99, db=db_session)
    # 不应抛错；命中全局缓存为空时回退 Mock
    assert svc is not None


def test_priority_picks_highest(db_session: Session):
    p_low = _seed_provider(db_session, "lowp", "low-model")
    p_high = _seed_provider(db_session, "highp", "high-model")
    db_session.add(ModelRole(
        project_id=5, provider_id=p_low.id,
        role="planner", model_name="low-planner", priority=1,
    ))
    db_session.add(ModelRole(
        project_id=5, provider_id=p_high.id,
        role="planner", model_name="high-planner", priority=9,
    ))
    db_session.commit()

    mgr = LLMServiceManager()
    svc = mgr.get_service_for("planner", project_id=5, db=db_session)
    assert svc.model_name == "high-planner"


def test_no_project_id_uses_global_service():
    mgr = LLMServiceManager()
    # project_id 为 None 时直接走 get_service，返回 Mock（未初始化）
    svc = mgr.get_service_for("critic", project_id=None, db=None)
    assert svc is not None
