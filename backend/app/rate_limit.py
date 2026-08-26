# backend/app/rate_limit.py
"""
Fixed-window rate limiting keyed by org (when auth is enforced) or client IP
(anonymous/default-org mode), per docs/v2/BACKEND.md's quota requirement.

Fails open: if Redis is unreachable, the request is allowed through and a
warning is logged, rather than making the whole API's availability depend on
Redis at this early stage.
"""
from __future__ import annotations

import logging
import time
from functools import lru_cache

import redis

from app.config import get_settings

logger = logging.getLogger("legalai.rate_limit")


@lru_cache
def get_redis_client() -> redis.Redis:
    return redis.Redis.from_url(get_settings().REDIS_URL, socket_connect_timeout=0.5, socket_timeout=0.5)


def check_rate_limit(key: str) -> None:
    """Raises RateLimitExceeded if `key` has exceeded the per-minute budget."""
    settings = get_settings()
    if not settings.REDIS_URL:
        return  # rate limiting disabled (e.g. local dev/tests with no Redis)

    window = int(time.time() // 60)
    redis_key = f"ratelimit:{key}:{window}"

    try:
        client = get_redis_client()
        count = client.incr(redis_key)
        if count == 1:
            client.expire(redis_key, 60)
    except Exception as e:
        logger.warning("Rate limiter unavailable (%s); failing open.", e)
        return

    if count > settings.RATE_LIMIT_PER_MINUTE:
        raise RateLimitExceeded(settings.RATE_LIMIT_PER_MINUTE)


class RateLimitExceeded(Exception):
    def __init__(self, limit: int):
        self.limit = limit
        super().__init__(f"Rate limit of {limit} requests/minute exceeded.")
