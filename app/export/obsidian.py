"""Obsidian console export (spec §42).

Generates the 17-file human-oversight vault from the live database. The vault is
a *view*: every number links back to the platform (ids included) and nothing
here writes back to the DB (§42: Obsidian 是人类总览层).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.corpus import Book, Chapter, Scene
from app.models.enums import HypothesisStatus, KnowledgeTier
from app.models.knowledge_registry import KnowledgeRule
from app.models.research import Experiment, Hypothesis
from app.models.research import Artifact
from app.models.technique import Technique

_VAULT_DIR = Path(__file__).resolve().parents[2] / "data" / "obsidian_vault"

FILES = [
    "00_总仪表盘", "01_研究进展", "02_新发现", "03_待验证假设", "04_已验证规律",
    "05_反例库", "06_人物规律", "07_因果规律", "08_情绪规律", "09_关系规律",
    "10_悬念与信息差", "11_技法库", "12_Writer_Arena", "13_模型表现",
    "14_审美模型", "15_失败研究", "16_系统健康",
]


def export_vault(db: Session, directory: Optional[Path] = None) -> dict:
    out_dir = Path(directory) if directory else _VAULT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    counts = {
        "books": db.scalar(select(func.count()).select_from(Book)) or 0,
        "chapters": db.scalar(select(func.count()).select_from(Chapter)) or 0,
        "scenes": db.scalar(select(func.count()).select_from(Scene)) or 0,
        "techniques": db.scalar(select(func.count()).select_from(Technique)) or 0,
        "rules": db.scalar(select(func.count()).select_from(KnowledgeRule)) or 0,
        "hypotheses": db.scalar(select(func.count()).select_from(Hypothesis)) or 0,
        "experiments": db.scalar(select(func.count()).select_from(Experiment)) or 0,
        "artifacts": db.scalar(select(func.count()).select_from(Artifact)) or 0,
    }

    written: list[str] = []

    def write(name: str, body: str) -> None:
        (out_dir / f"{name}.md").write_text(body, encoding="utf-8")
        written.append(f"{name}.md")

    write("00_总仪表盘", _dashboard(counts))
    write("01_研究进展", _research_progress(db))
    write("02_新发现", _new_findings(db))
    write("03_待验证假设", _pending_hypotheses(db))
    write("04_已验证规律", _validated_rules(db))
    write("05_反例库", _counterexamples(db))
    write("15_失败研究", _failures(db))
    write("11_技法库", _techniques(db))
    write("16_系统健康", _system_health(db))
    # Placeholder views until their EPIC data accumulates.
    for name in ["06_人物规律", "07_因果规律", "08_情绪规律", "09_关系规律",
                 "10_悬念与信息差", "12_Writer_Arena", "13_模型表现", "14_审美模型"]:
        write(name, f"# {name.split('_', 1)[1]}\n\n> 待相应 EPIC 数据积累后自动填充（§42）。\n")

    return {"directory": str(out_dir), "files": written, "counts": counts}


def _dashboard(counts: dict) -> str:
    lines = ["# 总仪表盘", "", "| 指标 | 数量 |", "|---|---|"]
    for key, val in counts.items():
        lines.append(f"| {key} | {val} |")
    lines += ["", "> 数据由 Novel Genome 自动导出（§42），只读。"]
    return "\n".join(lines) + "\n"


def _research_progress(db: Session) -> str:
    rows = db.scalars(select(Hypothesis)).all()
    by_status: dict[str, int] = {}
    for h in rows:
        by_status[h.status.value] = by_status.get(h.status.value, 0) + 1
    lines = ["# 研究进展", ""]
    for status, count in sorted(by_status.items()):
        lines.append(f"- {status}: {count}")
    if not rows:
        lines.append("_暂无假设。_")
    return "\n".join(lines) + "\n"


def _new_findings(db: Session) -> str:
    rules = db.scalars(
        select(KnowledgeRule).where(KnowledgeRule.tier.in_(
            [KnowledgeTier.CANDIDATE, KnowledgeTier.SUPPORTED, KnowledgeTier.REPLICATED]
        ))
    ).all()
    lines = ["# 新发现", ""]
    for r in rules:
        lines.append(f"- **{r.name}** ({r.tier.value}) — {r.statement} `[{r.id}]`")
    if not rules:
        lines.append("_暂无。_")
    return "\n".join(lines) + "\n"


def _pending_hypotheses(db: Session) -> str:
    rows = db.scalars(select(Hypothesis).where(Hypothesis.status == HypothesisStatus.PROPOSED)).all()
    lines = ["# 待验证假设", ""]
    for h in rows:
        lines.append(f"- {h.statement} `[{h.id}]`")
    if not rows:
        lines.append("_暂无待验证假设。_")
    return "\n".join(lines) + "\n"


def _validated_rules(db: Session) -> str:
    rows = db.scalars(
        select(KnowledgeRule).where(KnowledgeRule.tier.in_(
            [KnowledgeTier.VALIDATED, KnowledgeTier.PRODUCTION_PROVEN]
        ))
    ).all()
    lines = ["# 已验证规律", ""]
    for r in rows:
        lines.append(f"- **{r.name}** ({r.tier.value}): {r.statement} `[{r.id}]`")
    if not rows:
        lines.append("_尚无 VALIDATED+ 规律。_")
    return "\n".join(lines) + "\n"


def _counterexamples(db: Session) -> str:
    rules = db.scalars(select(KnowledgeRule)).all()
    lines = ["# 反例库", ""]
    total = 0
    for r in rules:
        for ce in r.counterexamples or []:
            total += 1
            lines.append(f"- **{r.name}** `[{r.id}]`: {ce.get('observation', '')}")
    if not total:
        lines.append("_反例库为空（注意 §51：无反例的技法不进生产）。_")
    return "\n".join(lines) + "\n"


def _failures(db: Session) -> str:
    rejected = db.scalars(
        select(KnowledgeRule).where(KnowledgeRule.tier == KnowledgeTier.REJECTED)
    ).all()
    deprecated = db.scalars(
        select(KnowledgeRule).where(KnowledgeRule.tier == KnowledgeTier.DEPRECATED)
    ).all()
    lines = ["# 失败研究", ""]
    for r in rejected + deprecated:
        reason = (r.scope or {}).get("demotion_reason", "")
        lines.append(f"- **{r.name}** ({r.tier.value}): {reason} `[{r.id}]`")
    if not rejected and not deprecated:
        lines.append("_暂无失败/废弃记录。_")
    return "\n".join(lines) + "\n"


def _techniques(db: Session) -> str:
    rows = db.scalars(select(Technique).order_by(Technique.confidence.desc())).all()
    lines = ["# 技法库", ""]
    for t in rows:
        lines.append(f"- **{t.name}** ({t.category.value}, {t.status.value}) — {t.definition} `[{t.id}]`")
    if not rows:
        lines.append("_暂无技法。_")
    return "\n".join(lines) + "\n"


def _system_health(db: Session) -> str:
    exp = db.scalar(select(func.count()).select_from(Experiment)) or 0
    art = db.scalar(select(func.count()).select_from(Artifact)) or 0
    return (
        "# 系统健康\n\n"
        f"- experiments: {exp}\n"
        f"- artifacts: {art}\n"
        "- knowledge_gate: P-10 生效（仅 VALIDATED+ 可被 NovelForge 消费）\n"
    )
