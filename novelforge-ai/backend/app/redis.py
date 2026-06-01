"""NovelForge AI - Redis"""
import os

import redis.asyncio as aioredis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


async def get_redis() -> aioredis.Redis:
    return aioredis.from_url(
        REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )
