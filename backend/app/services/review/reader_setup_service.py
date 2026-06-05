"""
P6 Reader Agent Setup Service
初始化 5 个 reader + 1 chief moderator 的 ModelRole + ReaderAgentProfile
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.comment_review import ReaderAgentProfile
from app.models.model_config import ModelProvider, ModelRole
from app.models.prompt_template import PromptTemplate
from app.utils.time_utils import utc_now


# 5 个 reader 维度 + 1 个 chief moderator
P6_READER_AGENTS = [
    {
        "reader_key": "reader_hook",
        "role": "reader_hook",
        "display_name": "钩子读者 Agent",
        "dimension": "开头/结尾/章内小钩子",
        "prompt_role": "reader_hook_comment",
    },
    {
        "reader_key": "reader_emotion",
        "role": "reader_emotion",
        "display_name": "情绪读者 Agent",
        "dimension": "人物动机/关系/情绪",
        "prompt_role": "reader_emotion_comment",
    },
    {
        "reader_key": "reader_logic",
        "role": "reader_logic",
        "display_name": "逻辑读者 Agent",
        "dimension": "设定自洽/因果/伏笔",
        "prompt_role": "reader_logic_comment",
    },
    {
        "reader_key": "reader_commercial",
        "role": "reader_commercial",
        "display_name": "商业读者 Agent",
        "dimension": "节奏/留存/爽点",
        "prompt_role": "reader_commercial_comment",
    },
    {
        "reader_key": "reader_toxic",
        "role": "reader_toxic",
        "display_name": "毒点读者 Agent",
        "dimension": "毒点/解释腔/工具人",
        "prompt_role": "reader_toxic_comment",
    },
]

P6_CHIEF_MODERATOR = {
    "reader_key": "chief_comment_moderator",
    "role": "chief_comment_moderator",
    "display_name": "主 Agent · 评论接入官",
    "dimension": "评论分流/回复/裁决",
    "prompt_role": "chief_comment_triage",
}


def _ensure_model_role(db: Session, *, role_key: str) -> ModelRole:
    """确保全局 ModelRole 存在 (不绑定 provider, 留给用户在模型配置页绑定)."""
    existing = db.query(ModelRole).filter(
        ModelRole.role == role_key,
        ModelRole.project_id == None,
    ).first()
    if existing:
        return existing
    role = ModelRole(
        role=role_key,
        provider_id=None,
        model_name="",
        temperature=0.7,
        max_tokens=2000,
        priority=50,
        assignment_mode="auto",
        preferred_quality="balanced",
        updated_by="p6_seed",
    )
    db.add(role)
    db.flush()
    return role


def _ensure_prompt_template(db: Session, prompt_role: str) -> Optional[PromptTemplate]:
    """获取全局 active prompt template."""
    return db.query(PromptTemplate).filter(
        PromptTemplate.role == prompt_role,
        PromptTemplate.project_id == None,
        PromptTemplate.is_active == 1,
    ).first()


def _ensure_reader_profile(
    db: Session,
    *,
    model_role: ModelRole,
    reader_key: str,
    display_name: str,
    dimension: str,
) -> ReaderAgentProfile:
    """确保 ReaderAgentProfile 存在, 1:1 with ModelRole."""
    existing = db.query(ReaderAgentProfile).filter(
        ReaderAgentProfile.agent_role_id == model_role.id,
    ).first()
    if existing:
        return existing
    profile = ReaderAgentProfile(
        agent_role_id=model_role.id,
        reader_key=reader_key,
        display_name=display_name,
        dimension=dimension,
        weight=1.0,
        adopted_count=0,
        rejected_count=0,
        generated_comment_count=0,
        enabled=True,
    )
    db.add(profile)
    db.flush()
    return profile


def seed_p6_reader_agents(db: Session) -> List[ReaderAgentProfile]:
    """初始化 5 reader + 1 chief moderator 的 ModelRole + ReaderAgentProfile.

    不会绑定 Provider/Model — 留给用户在 P7 模型配置页自行绑定。
    不会默认走 mock — 避免假装能跑。
    """
    profiles = []
    for spec in P6_READER_AGENTS + [P6_CHIEF_MODERATOR]:
        role = _ensure_model_role(db, role_key=spec["role"])
        # 验证 prompt template 存在 (失败也继续, 不阻塞初始化)
        tpl = _ensure_prompt_template(db, spec["prompt_role"])
        if not tpl:
            print(f"[P6 Seed] WARN: prompt template {spec['prompt_role']} 不存在")
        profile = _ensure_reader_profile(
            db,
            model_role=role,
            reader_key=spec["reader_key"],
            display_name=spec["display_name"],
            dimension=spec["dimension"],
        )
        profiles.append(profile)
    db.commit()
    print(f"[P6 Seed] 完成: {len(profiles)} 个 reader/moderator profile")
    return profiles


def get_enabled_reader_profiles(db: Session) -> List[ReaderAgentProfile]:
    """获取所有启用的 reader profile (不含 chief moderator)."""
    reader_keys = [s["reader_key"] for s in P6_READER_AGENTS]
    return db.query(ReaderAgentProfile).filter(
        ReaderAgentProfile.reader_key.in_(reader_keys),
        ReaderAgentProfile.enabled == True,
    ).all()


def get_chief_moderator_profile(db: Session) -> Optional[ReaderAgentProfile]:
    """获取 chief moderator profile."""
    return db.query(ReaderAgentProfile).filter(
        ReaderAgentProfile.reader_key == "chief_comment_moderator",
    ).first()
