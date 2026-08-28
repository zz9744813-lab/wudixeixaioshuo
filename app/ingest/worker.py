"""Ingest worker (spec §40: ``ingest_worker`` / ``ingest`` queue).

A local, Redis-free queue drainer. The synchronous API finalizes ingest within
the request, so this worker is the out-of-band path: process any ``PENDING``
ingest tasks (e.g. enqueued via :func:`enqueue_ingest`, or replayed after a
restart). It is intentionally simple — one pass over the queue, failures route to
the dead-letter table (spec 禁止11, no infinite retry).
"""
from __future__ import annotations

from sqlalchemy import select

from app.db import SessionLocal
from app.ingest.service import process_task
from app.models.enums import TaskStatus
from app.models.infra import Task


def drain_ingest_queue(limit: int = 10, *, db=None) -> int:
    """Drain up to ``limit`` PENDING ingest tasks. Returns the number processed.

    If ``db`` is provided it is reused (caller manages the transaction/session);
    otherwise a short-lived session is opened per call.
    """
    own_session = db is None
    session = db or SessionLocal()
    processed = 0
    try:
        pending = session.scalars(
            select(Task).where(Task.queue == "ingest", Task.status == TaskStatus.PENDING).limit(limit)
        ).all()
        for task in pending:
            process_task(session, task)
            processed += 1
        return processed
    finally:
        if own_session:
            session.close()
