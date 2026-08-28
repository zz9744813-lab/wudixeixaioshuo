"""Run Registry (spec §36 EPIC-A, §35 Provenance).

Every Agent invocation is a :class:`Run`; every LLM call is a :class:`ModelCall`.
Together they form the provenance chain required by spec §35:

    CharacterState -> Claim -> AgentRun -> ContextPackage -> Evidence ->
    Scene -> Chapter -> Book

The functions here persist those rows so no research output is untraceable
and no task is duplicated (idempotency_key).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.ids import run_id


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_run(
    db: Session,
    task_type: str,
    *,
    parent_task: Optional[str] = None,
    prompt_version: Optional[str] = None,
    context_package_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    input_ref: Optional[dict] = None,
) -> "Any":
    from app.models.infra import Run

    run = Run(
        id=run_id(),
        task_type=task_type,
        parent_task=parent_task,
        prompt_version=prompt_version,
        context_package_id=context_package_id,
        idempotency_key=idempotency_key,
        status="RUNNING",
        input_ref=input_ref or {},
        started_at=_now(),
    )
    db.add(run)
    db.flush()
    return run


def finalize_run(
    db: Session,
    run: "Any",
    status: str,
    *,
    output_ref: Optional[dict] = None,
    confidence: Optional[float] = None,
    warnings: Optional[list] = None,
    uncertainties: Optional[list] = None,
) -> None:
    from app.models.enums import TaskStatus

    run.status = TaskStatus(status).value if status in TaskStatus.__members__ else status
    run.output_ref = output_ref or {}
    run.confidence = confidence
    run.warnings = warnings or []
    run.uncertainties = uncertainties or []
    run.finished_at = _now()
    db.flush()


def log_model_call(
    db: Session,
    run_id_: str,
    model: str,
    prompt_version: str,
    input_payload: dict,
    output_payload: dict,
    schema_version: str,
    *,
    parent_task: Optional[str] = None,
    derived_artifacts: Optional[list] = None,
    error: Optional[str] = None,
) -> "Any":
    from app.models.infra import ModelCall

    call = ModelCall(
        id=run_id().replace("RUN-", "MC-"),
        run_id=run_id_,
        model=model,
        prompt_version=prompt_version,
        parent_task=parent_task,
        input_payload=input_payload,
        output_payload=output_payload,
        schema_version=schema_version,
        derived_artifacts=derived_artifacts or [],
        error=error,
        called_at=_now(),
    )
    db.add(call)
    db.flush()
    return call
