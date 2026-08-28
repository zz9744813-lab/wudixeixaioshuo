"""Ingest worker (spec §40: ``ingest_worker`` / ``ingest`` queue).

Two dispatch modes behind one drainer:

* **Redis** (spec §40's real queue): pops task ids pushed by
  :func:`enqueue_ingest`; the DB task row remains the source of truth.
* **Local fallback** (no Redis configured or Redis down): scans
  ``tasks WHERE queue='ingest' AND status=PENDING`` directly.

Failures land in the dead-letter table (禁止11: no infinite retry).
"""
from __future__ import annotations

from sqlalchemy import select

from app.core.queue import get_queue
from app.db import SessionLocal
from app.ingest.service import process_task
from app.models.enums import TaskStatus
from app.models.infra import Task


def drain_ingest_queue(limit: int = 10, *, db=None) -> int:
    """Process up to ``limit`` pending ingest tasks. Returns the number processed.

    With Redis configured, pops dispatch notifications first; any remaining
    budget scans the DB (so tasks enqueued while Redis was down still run).
    """
    own_session = db is None
    session = db or SessionLocal()
    processed = 0
    try:
        queue = get_queue()
        popped: list[str] = []
        if queue.name == "redis":
            while processed + len(popped) < limit:
                task_id = queue.pop(timeout=1.0)
                if task_id is None:
                    break
                popped.append(task_id)
            for task_id in popped:
                task = session.get(Task, task_id)
                if task is not None and task.status == TaskStatus.PENDING:
                    process_task(session, task)
                    processed += 1
        if processed < limit:
            pending = session.scalars(
                select(Task)
                .where(Task.queue == "ingest", Task.status == TaskStatus.PENDING)
                .limit(limit - processed)
            ).all()
            for task in pending:
                process_task(session, task)
                processed += 1
        return processed
    finally:
        if own_session:
            session.close()
