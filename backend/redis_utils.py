from __future__ import annotations

import json
import logging
from typing import Any, Optional

from config import settings

try:
    import redis  # type: ignore
except Exception:
    redis = None  # type: ignore


logger = logging.getLogger(__name__)

_redis_client: Optional["redis.Redis"] = None


def get_redis_client() -> Optional["redis.Redis"]:
    """Return a singleton Redis client or None if unavailable.

    Using decode_responses=True so values are str; JSON helpers convert to/from str.
    """
    global _redis_client
    if redis is None:
        return None
    if _redis_client is not None:
        return _redis_client
    try:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        # Ping to validate connectivity
        _redis_client.ping()
        return _redis_client
    except Exception:
        logger.warning("Redis unavailable at %s; continuing without cache/queue", settings.REDIS_URL)
        return None


# -----------------------------
# JSON cache helpers
# -----------------------------
def cache_get_json(key: str) -> Optional[Any]:
    client = get_redis_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception:
        return None


def cache_set_json(key: str, value: Any, ttl_seconds: int) -> None:
    client = get_redis_client()
    if client is None:
        return
    try:
        client.set(key, json.dumps(value), ex=ttl_seconds)
    except Exception:
        pass


def cache_delete(key: str) -> None:
    client = get_redis_client()
    if client is None:
        return
    try:
        client.delete(key)
    except Exception:
        pass


def cache_invalidate_by_pattern(pattern: str) -> None:
    client = get_redis_client()
    if client is None:
        return
    try:
        cursor = 0
        while True:
            cursor, keys = client.scan(cursor=cursor, match=pattern, count=500)
            if keys:
                client.delete(*keys)
            if cursor == 0:
                break
    except Exception:
        pass


# -----------------------------
# Simple queue for PDF analysis jobs
# -----------------------------
QUEUE_KEY = "queue:pdf_analysis"
JOB_KEY_PREFIX = "job:pdf:"


def enqueue_pdf_job(payload: dict) -> Optional[str]:
    """Enqueue a PDF analysis job. Returns job id or None if Redis unavailable.

    Payload must already include an "id" field; this function stores metadata and pushes to queue.
    """
    client = get_redis_client()
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
        client.hset(job_key, mapping={k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) for k, v in {**payload, **meta}.items()})
        client.rpush(QUEUE_KEY, job_id)
        # Optional expiry for job metadata (7 days)
        client.expire(job_key, 7 * 24 * 3600)
        return job_id
    except Exception:
        return None


def get_job_status(job_id: str) -> Optional[dict[str, Any]]:
    client = get_redis_client()
    if client is None:
        return None
    try:
        raw = client.hgetall(JOB_KEY_PREFIX + job_id)
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
        return None


def update_job(job_id: str, **fields: Any) -> None:
    client = get_redis_client()
    if client is None:
        return
    try:
        job_key = JOB_KEY_PREFIX + job_id
        client.hset(job_key, mapping={k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) for k, v in fields.items()})
    except Exception:
        pass


