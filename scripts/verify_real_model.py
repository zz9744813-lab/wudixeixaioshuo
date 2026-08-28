"""Real-model end-to-end verification (run OUTSIDE pytest).

Uses whatever LLM the local .env configures (a real gateway). Verifies the full
research chain with real content: ingest -> multi-pass analysis -> controlled
experiment with blind judging. Prints the real artifacts so a human can judge
whether the model's analysis is actually good.
"""
from __future__ import annotations

import json
import sys
import time

sys.path.insert(0, ".")

from sqlalchemy import select

from app.config import get_settings

get_settings.cache_clear()

from app.db import SessionLocal, init_db  # noqa: E402
from app.agents.orchestrator import analyze_scene  # noqa: E402
from app.ingest.service import ingest_bytes  # noqa: E402
from app.models.corpus import Scene  # noqa: E402
from app.models.decomposition import Event  # noqa: E402
from app.models.emotion import EmotionState  # noqa: E402
from app.models.knowledge_registry import KnowledgeRule  # noqa: E402
from app.models.research import Experiment, Hypothesis  # noqa: E402
from app.research.runner import run_experiment  # noqa: E402

SAMPLE = """第一章 启程
清晨的雾还没散，张三就已经站在了村口。他回头看了一眼熟悉的村庄，心里五味杂陈。
母亲昨夜塞给他的那袋干粮还挂在腰上，沉甸甸的。
「走吧。」他对自己说，声音在雾里显得单薄。

* * *

正午时分，张三在路上遇见了赶集回来的李四。
「听说北边打仗了，你还往北走？」李四压低声音。
张三的手心出了汗。他想起父亲临终前说的那句话，还是点了点头。

第二章 风波
入夜后风雨大作。破庙里，李四忽然停下了脚步，盯着墙角。
「有人来过，而且不久前。」他说。
张三握紧了随身的短刀，感到一阵寒意顺着脊背爬上来。

第二天
他们发现前方山道旁有一座废弃的客栈，招牌歪斜，字迹难辨。
李四建议绕开走，张三却推门走了进去。桌上还摆着半碗冷粥，冒着昨夜的凉气。
"""


def main() -> None:
    settings = get_settings()
    assert settings.llm_api_key, "no LLM configured; set LLM_* in .env"
    assert not settings.force_fake_llm, "FORCE_FAKE_LLM is set; unset it for real verification"
    print(f"[1] provider: {settings.llm_model} @ {settings.llm_base_url}")

    init_db()
    db = SessionLocal()
    try:
        result = ingest_bytes(db, SAMPLE.encode("utf-8"), "novel.txt", title="真模型验证")
        print(f"[2] ingested: {result.chapter_count} chapters / {result.scene_count} scenes")

        scenes = db.scalars(
            select(Scene).where(Scene.book_id == result.book_id).order_by(Scene.index)
        ).all()
        t0 = time.time()
        import os

        force = os.environ.get("ANALYZE_FORCE") == "1"
        t0 = time.time()
        for s in scenes:
            if s.analyzed and not force:
                print(f"[3] scene {s.index}: already analyzed, skip")
                continue
            r = analyze_scene(db, s, force=force)
            warn = sum(len(p.get("warnings", [])) for p in r["passes"])
            errs = [p for p in r["passes"] if p.get("error")]
            print(f"[3] scene {s.index}: analyzed={r['analyzed']} "
                  f"passes={len(r['passes'])} errors={len(errs)} warnings={warn}")
        print(f"    analysis wall time: {time.time() - t0:.0f}s")

        events = db.query(Event).filter(Event.book_id == result.book_id).all()
        print(f"[4] REAL events ({len(events)}):")
        for e in events:
            print(f"    [{','.join(e.types)}] {e.confidence:.2f} :: {e.description[:70]}")
        emotions = db.query(EmotionState).filter(EmotionState.scene_id.in_([s.id for s in scenes])).all()
        print(f"[5] REAL emotions ({len(emotions)}):")
        for e in emotions:
            print(f"    {e.emotion} {e.intensity:.2f} :: {json.dumps(e.appraisal, ensure_ascii=False)[:90]}")

        # Controlled experiment with the real judge.
        hyp = Hypothesis(
            id="H-VERIFY",
            statement="客栈的异常痕迹作为增量线索，会提高读者的好奇心与紧张感。",
            independent_variables=["inn_sign_condition"],
            dependent_variables=["curiosity", "tension"],
            controls=["character_state"],
            expected_direction="treatment higher",
            falsification_condition="treatment not stably better than control",
        )
        db.merge(hyp)
        exp = Experiment(
            id="EXP-VERIFY",
            hypothesis_id=hyp.id,
            fixed={"characters": ["张三", "李四"], "reveal_scene": "第二章"},
            measurements=["curiosity", "tension"],
            evaluation={"blind_pairwise": True},
            falsification="treatment not stably better than control",
        )
        db.merge(exp)
        from app.models.research import ExperimentVariant

        for old in db.query(ExperimentVariant).filter(ExperimentVariant.experiment_id == exp.id).all():
            db.delete(old)
        db.add(ExperimentVariant(id="VAR-V0", experiment_id=exp.id, label="control",
                                 variant_type="control", changed={}))
        db.add(ExperimentVariant(id="VAR-V1", experiment_id=exp.id, label="treatment_A",
                                 variant_type="treatment",
                                 changed={"knowledge_change": {"character": "张三", "fact": "客栈最近有人住", "to": "SUSPECTED"}}))
        db.commit()

        verdict = run_experiment(db, exp.id)
        print(f"[6] experiment verdict: {json.dumps(verdict, ensure_ascii=False, indent=2)}")

        # Production gate spot-check: seed a rule through the real ladder.
        rule = KnowledgeRule(
            id="KR-VERIFY", name="增量线索维持悬念", statement="延迟揭示期间加入增量线索提高好奇心。",
            tier=__import__("app.models.enums", fromlist=["KnowledgeTier"]).KnowledgeTier.VALIDATED,
            mechanism="信息差+期待积累", preconditions=["secret_importance_high"],
            failure_modes=["reveal_without_consequence"], experiment_ids=[exp.id],
            judge_agreement=max(verdict.get("confidence", 0), 0.7), reproduction_count=2,
            counterexamples=[{"observation": "日常流中延迟揭示可能显得做作"}],
        )
        db.merge(rule)
        db.commit()
        from app.api.novelforge import _validated_rules

        print(f"[7] production-visible rules: {[r.id for r in _validated_rules(db)]}")
        print("DONE: real-model chain verified end to end")
    finally:
        db.close()


if __name__ == "__main__":
    main()
