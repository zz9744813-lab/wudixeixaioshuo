"""Knowledge promotion gate (spec §26, §51, §63).

Ladder (§63):

    OBSERVATION → CANDIDATE   needs mechanism            (缺机制 → 保持)
    CANDIDATE   → SUPPORTED   needs evidence             (无证据 → 保持)
    SUPPORTED   → REPLICATED  needs counterexample search
                              + cross-sample reproduction (无反例搜索 → 不晋升)
    REPLICATED  → VALIDATED   needs a controlled experiment + independent judge
                              (无受控实验 → 不晋升)
    VALIDATED   → PRODUCTION_PROVEN needs real production evidence
                              (NovelForge 实际失败 → 降级)

Only VALIDATED+ may feed NovelForge (P-10, §26.1). Every refusal returns the
missing requirements so the operator knows exactly what to add.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.enums import KnowledgeTier
from app.models.knowledge_registry import KnowledgeRule

JUDGE_AGREEMENT_THRESHOLD = 0.6
MIN_REPRODUCTIONS = 2


def _next_tier(current: KnowledgeTier) -> KnowledgeTier | None:
    order = [
        KnowledgeTier.OBSERVATION,
        KnowledgeTier.CANDIDATE,
        KnowledgeTier.SUPPORTED,
        KnowledgeTier.REPLICATED,
        KnowledgeTier.VALIDATED,
        KnowledgeTier.PRODUCTION_PROVEN,
    ]
    if current not in order:
        return None
    idx = order.index(current)
    return order[idx + 1] if idx + 1 < len(order) else None


def gate_requirements(rule: KnowledgeRule, target: KnowledgeTier) -> list[str]:
    """Return the list of unmet requirements for reaching ``target`` (empty = pass)."""
    missing: list[str] = []
    if target == KnowledgeTier.CANDIDATE:
        if not (rule.mechanism or "").strip():
            missing.append("mechanism is required (§63: 缺机制 → 保持)")
    elif target == KnowledgeTier.SUPPORTED:
        if not rule.evidence:
            missing.append("evidence is required (§63: 无证据 → 保持)")
    elif target == KnowledgeTier.REPLICATED:
        if not rule.counterexamples:
            missing.append("counterexample search required (§63: 无反例搜索 → 不晋升)")
        if rule.reproduction_count < MIN_REPRODUCTIONS:
            missing.append(
                f"cross-sample reproduction required (§51: have {rule.reproduction_count}, "
                f"need {MIN_REPRODUCTIONS})"
            )
    elif target == KnowledgeTier.VALIDATED:
        if not rule.experiment_ids:
            missing.append("a controlled experiment is required (§63: 无受控实验 → 不晋升)")
        if rule.judge_agreement <= 0:
            missing.append("an independent judge verdict is required (§51)")
        elif rule.judge_agreement < JUDGE_AGREEMENT_THRESHOLD:
            missing.append(
                f"judge agreement {rule.judge_agreement:.2f} below threshold "
                f"{JUDGE_AGREEMENT_THRESHOLD:.2f}"
            )
    elif target == KnowledgeTier.PRODUCTION_PROVEN:
        if not rule.production_evidence:
            missing.append("real NovelForge production evidence is required (§44)")
    return missing


def promote(db: Session, rule_id: str) -> dict:
    """Attempt one ladder step. Never skips tiers; returns the decision + reasons."""
    rule = db.get(KnowledgeRule, rule_id)
    if rule is None:
        raise ValueError("rule not found")
    target = _next_tier(rule.tier)
    if target is None:
        return {
            "rule_id": rule.id,
            "from": rule.tier.value,
            "to": rule.tier.value,
            "promoted": False,
            "reason": "already at the top of the ladder (or rejected/deprecated)",
        }
    missing = gate_requirements(rule, target)
    if missing:
        return {
            "rule_id": rule.id,
            "from": rule.tier.value,
            "to": target.value,
            "promoted": False,
            "reason": "gate not passed",
            "missing": missing,
        }
    rule.tier = target
    db.add(rule)
    db.commit()
    return {"rule_id": rule.id, "from": rule.tier.value, "to": target.value, "promoted": True}


def demote(db: Session, rule_id: str, reason: str, *, to: KnowledgeTier = KnowledgeTier.DEPRECATED) -> dict:
    rule = db.get(KnowledgeRule, rule_id)
    if rule is None:
        raise ValueError("rule not found")
    rule.tier = to
    rule.scope = {**(rule.scope or {}), "demotion_reason": reason}
    db.add(rule)
    db.commit()
    return {"rule_id": rule.id, "to": to.value, "reason": reason}


def add_counterexample(db: Session, rule_id: str, observation: str, evidence: list | None = None) -> dict:
    """Register a counterexample (spec §51: a mature rule must have one)."""
    rule = db.get(KnowledgeRule, rule_id)
    if rule is None:
        raise ValueError("rule not found")
    entry = {"observation": observation, "evidence": evidence or []}
    rule.counterexamples = list(rule.counterexamples or []) + [entry]
    db.add(rule)
    db.commit()
    return {"rule_id": rule.id, "counterexample_count": len(rule.counterexamples)}


def gate_checklist(db: Session, rule_id: str) -> dict:
    """The §51 research-quality checklist with live pass/fail per item."""
    rule = db.get(KnowledgeRule, rule_id)
    if rule is None:
        raise ValueError("rule not found")
    checklist = {
        "mechanism_明确": bool((rule.mechanism or "").strip()),
        "preconditions_明确": bool(rule.preconditions),
        "failure_modes_明确": bool(rule.failure_modes),
        "多个_source_evidence": len(rule.evidence or []) >= 2,
        "有_counterexample": bool(rule.counterexamples),
        "有_反事实实验": bool(rule.experiment_ids),
        "有_独立_judge": rule.judge_agreement >= JUDGE_AGREEMENT_THRESHOLD,
        "跨样本复现": rule.reproduction_count >= MIN_REPRODUCTIONS,
        "达到_VALIDATED": rule.tier
        in (KnowledgeTier.VALIDATED, KnowledgeTier.PRODUCTION_PROVEN),
    }
    return {"rule_id": rule.id, "tier": rule.tier.value, "checklist": checklist}
