from __future__ import annotations

import json
import logging
from typing import Any, Optional, cast

from config import settings
import redis.asyncio as redis
from redis.asyncio import Redis as AsyncRedis

logger = logging.getLogger(__name__)

_redis_client: Optional[AsyncRedis] = None


async def get_redis_client() -> Optional[AsyncRedis]:
    """Return a singleton Redis client or None if unavailable.

    Using decode_responses=True so values are str; JSON helpers convert to/from str.
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        # Cast to the asyncio Redis client type so type checkers know awaited methods are coroutines
        _redis_client = cast(AsyncRedis, redis.from_url(settings.REDIS_URL, decode_responses=True))
        # Ping to validate connectivity
        await _redis_client.ping()
        return _redis_client
    except Exception:
        logger.warning("Redis unavailable at %s; continuing without cache/queue", settings.REDIS_URL)
        return None


# -----------------------------
# JSON cache helpers
# -----------------------------
async def cache_get_json(key: str) -> Optional[Any]:
    client = await get_redis_client()
    if client is None:
        return None
    try:
        raw = await client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception:
        return None


async def cache_set_json(key: str, value: Any, ttl_seconds: int) -> None:
    client = await get_redis_client()
    if client is None:
        return
    try:
        await client.set(key, json.dumps(value), ex=ttl_seconds)
    except Exception:
        pass


async def cache_delete(key: str) -> None:
    client = await get_redis_client()
    if client is None:
        return
    try:
        await client.delete(key)
    except Exception:
        pass


async def cache_invalidate_by_pattern(pattern: str) -> None:
    client = await get_redis_client()
    if client is None:
        return
    try:
        cursor = 0
        while True:
            cursor, keys = await client.scan(cursor=cursor, match=pattern, count=500)
            if keys:
                await client.delete(*keys)
            if cursor == 0:
                break
    except Exception:
        pass


# -----------------------------
# Simple queue for PDF analysis jobs
# -----------------------------
QUEUE_KEY = "queue:pdf_analysis"
JOB_KEY_PREFIX = "job:pdf:"


async def enqueue_pdf_job(payload: dict) -> Optional[str]:
    """Enqueue a PDF analysis job. Returns job id or None if Redis unavailable.

    Payload must already include an "id" field; this function stores metadata and pushes to queue.
    """
    client = await get_redis_client()
    if client is None:
        return None
    job_id = payload.get("id")
    if not job_id:
        return None
    try:
        job_key = JOB_KEY_PREFIX + job_id
        # Initial job state
        meta = {
            "status": "queued",
            "progress": 0,
        }
        mapping = {k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) for k, v in {**payload, **meta}.items()}
        # Cast to Any to work around typing stub issues where asyncio methods are not annotated as awaitable
        await cast(Any, client).hset(job_key, mapping=mapping)
        await cast(Any, client).rpush(QUEUE_KEY, job_id)
        # Optional expiry for job metadata (7 days)
        await client.expire(job_key, 7 * 24 * 3600)
        return job_id
    except Exception:
        logger.exception("Error enqueuing job %s", job_id)
        return None


async def get_job_status(job_id: str) -> Optional[dict[str, Any]]:
    client = await get_redis_client()
    if client is None:
        return None
    try:
        # Work around typing: asyncio hgetall is awaitable at runtime
        raw = await cast(Any, client).hgetall(JOB_KEY_PREFIX + job_id)
        if not raw:
            return None
        result: dict[str, Any] = {}
        for k, v in raw.items():
            # Try to decode JSON values; fall back to raw string
            try:
                result[k] = json.loads(v)
            except Exception:
                result[k] = v
        return result
    except Exception:
        logger.exception("Error getting job status for %s", job_id)
        return None


async def update_job(job_id: str, **fields: Any) -> None:
    client = await get_redis_client()
    if client is None:
        return
    try:
        job_key = JOB_KEY_PREFIX + job_id
        mapping = {k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) for k, v in fields.items()}
        # Work around typing: asyncio hset is awaitable at runtime
        await cast(Any, client).hset(job_key, mapping=mapping)
    except Exception:
        logger.exception("Error updating job %s", job_id)
        pass
