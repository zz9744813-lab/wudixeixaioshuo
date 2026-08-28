"""Base Agent (spec §16, §31, §35).

Every analysis Pass is an Agent that:

1. assembles a :class:`ContextPackage` for the Scene (spec §30),
2. calls the LLM provider with a versioned prompt (spec §28),
3. parses the JSON response into its structured ``output_model``,
4. **records a ``Run`` + ``ModelCall``** so the output is fully traceable
   (spec §35, P-11),
5. persists its artifacts (Events / Perceptions / ...) with the run id.

The BaseAgent is generic; concrete Passes set ``agent_type``, ``prompt_id``,
``output_model`` and a ``persist`` callback (spec P-12: one concern per Agent).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional, Type

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.ids import context_package_id, new_id, run_id
from app.llm import get_provider
from app.llm.provider import LLMMessage, extract_json
from app.models.infra import ContextPackage, ModelCall, PromptRegistry, Run
from app.models.enums import TaskStatus


@dataclass
class AgentRunResult:
    agent_type: str
    run_id: str
    output: BaseModel
    raw: str
    confidence: float
    warnings: List[str] = field(default_factory=list)
    uncertainties: List[str] = field(default_factory=list)
    model: str = "fake"


class BaseAgent:
    agent_type: str = "base"
    prompt_id: str = "base"
    output_model: Type[BaseModel] = BaseModel
    # persist(db, scene, output, run_id) -> None
    persist: Callable[[Session, object, BaseModel, str], None] = lambda db, scene, out, rid: None

    def __init__(self, db: Session, provider=None) -> None:
        self.db = db
        self.provider = provider or get_provider(db=db)

    # ---- prompt loading (spec §28) -------------------------------------- #
    def _load_prompt(self) -> str:
        row = self.db.get(PromptRegistry, self.prompt_id)
        if row is None:
            # Prompt not bootstrapped yet; fall back to a generic instruction.
            return (
                f"You are the {self.agent_type} analyzer for a Scene of a novel. "
                "Return a JSON object matching the required schema."
            )
        return row.content

    # ---- context package (spec §30) -------------------------------------- #
    def _build_context(self, scene) -> ContextPackage:
        spans = scene.spans if scene.spans else []
        raw_text = "\n".join(s.text for s in spans) or (scene.summary or "")
        payload = {
            "book_id": scene.book_id,
            "chapter_id": scene.chapter_id,
            "scene_index": scene.index,
            "pov": scene.pov,
            "time": getattr(scene, "time", None),
            "location": scene.location,
            "participants": scene.participants,
            "scene_goal": getattr(scene, "scene_goal", None),
            "dominant_conflict": getattr(scene, "dominant_conflict", None),
            "entry_state": scene.entry_state or {},
            "summary": scene.summary,
            "raw_text": raw_text,
        }
        cp = ContextPackage(id=context_package_id(), task=self.agent_type, payload=payload)
        self.db.add(cp)
        self.db.flush()
        return cp

    # ---- run ------------------------------------------------------------- #
    def run(self, scene) -> AgentRunResult:
        prompt = self._load_prompt()
        cp = self._build_context(scene)
        import json as _json

        user_content = _json.dumps(cp.payload, ensure_ascii=False, default=str)
        messages = [
            LLMMessage(role="system", content=prompt),
            LLMMessage(role="user", content=user_content),
        ]
        raw = self.provider.complete(messages, output_model=self.output_model)

        data = extract_json(raw)
        warnings: List[str] = []
        if data is None:
            warnings.append("LLM response was not valid JSON; stored raw for review")
            data = {}
        try:
            out = self.output_model(**data)
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"output validation failed: {exc}")
            out = self.output_model()

        run = Run(
            id=run_id(),
            task_type=self.agent_type,
            prompt_version=self.prompt_id,
            context_package_id=cp.id,
            # Sub-agent runs don't claim idempotency: the orchestrator / experiment
            # runner owns the idempotency key (spec §33). NULL is allowed and
            # unique-constraint friendly.
            idempotency_key=getattr(self, "idempotency_key", None),
            status=TaskStatus.SUCCESS,
            input_ref={"scene_id": scene.id},
            output_ref={"agent_type": self.agent_type},
            confidence=getattr(out, "confidence", None),
        )
        self.db.add(run)
        self.db.flush()

        self.db.add(
            ModelCall(
                id=new_id("MC"),
                run_id=run.id,
                model=self.provider.name,
                prompt_version=self.prompt_id,
                input_payload={"messages": [m.model_dump() for m in messages]},
                output_payload={"raw": raw[:4000]},
                schema_version="1.0",
            )
        )

        self.persist(self.db, scene, out, run.id)
        self.db.flush()

        return AgentRunResult(
            agent_type=self.agent_type,
            run_id=run.id,
            output=out,
            raw=raw,
            confidence=getattr(out, "confidence", 0.0) or 0.0,
            warnings=warnings,
            model=self.provider.name,
        )
