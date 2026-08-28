"""Task queue backends (spec §40).

Two interchangeable backends behind one tiny interface:

* :class:`RedisTaskQueue` — real Redis (spec §40's ``ingest`` queue). The DB
  remains the source of truth (every task row lives in ``tasks``); Redis only
  carries dispatch notifications so a worker can pop them FIFO.
* :class:`LocalTaskQueue` — no Redis configured (or unreachable): workers fall
  back to scanning ``tasks WHERE status=PENDING``.

``get_queue()`` picks based on settings and live connectivity; a Redis outage
degrades to the local path instead of losing work (spec §34).
"""
from __future__ import annotations

from typing import Optional, Protocol

from app.config import get_settings


class TaskQueue(Protocol):
    name: str

    def enqueue(self, task_id: str) -> None: ...

    def pop(self, timeout: float = 1.0) -> Optional[str]:
        """Block up to ``timeout`` seconds; return a task id or None."""
        ...

    def depth(self) -> int: ...


class RedisTaskQueue:
    name = "redis"

    def __init__(self, redis_url: str, queue_key: str = "novel_genome:queue:ingest") -> None:
        import redis

        self._r = redis.Redis.from_url(redis_url, decode_responses=True, socket_timeout=2.0)
        self.queue_key = queue_key

    def enqueue(self, task_id: str) -> None:
        self._r.rpush(self.queue_key, task_id)

    def pop(self, timeout: float = 1.0) -> Optional[str]:
        item = self._r.blpop(self.queue_key, timeout=max(int(timeout), 1))
        if item is None:
            return None
        return item[1]

    def depth(self) -> int:
        return int(self._r.llen(self.queue_key))


class LocalTaskQueue:
    """DB-backed fallback: nothing to enqueue; pop() returns None and the
    worker falls through to scanning PENDING tasks."""

    name = "local"

    def enqueue(self, task_id: str) -> None:  # pragma: no cover - trivial
        return None

    def pop(self, timeout: float = 1.0) -> Optional[str]:  # pragma: no cover
        return None

    def depth(self) -> int:  # pragma: no cover
        return 0


def get_queue() -> TaskQueue:
    """Redis when configured AND reachable; local fallback otherwise."""
    settings = get_settings()
    if settings.redis_url:
        try:
            q = RedisTaskQueue(settings.redis_url)
            q._r.ping()
            return q
        except Exception:  # noqa: BLE001 — Redis down: degrade, don't lose work
            return LocalTaskQueue()
    return LocalTaskQueue()
