# backend/app/services/memory/session.py
"""
Session-tier memory (docs/v2/AGENTS.md's Memory system): short-term,
TTL-bound state scoped to one analysis session -- the last N chat turns, or
which document/clauses a caller currently has open. Redis-backed, fail-open
exactly like app/rate_limit.py's rate limiting (reuses its `get_redis_client`
so this doesn't open a second connection pool) -- an unreachable Redis must
never break a request; memory is an enhancement, not a dependency.
"""
from __future__ import annotations

import json
import logging
from typing import Any, List, Optional

from app.config import get_settings
from app.rate_limit import get_redis_client

logger = logging.getLogger("legalai.memory.session")

_KEY_PREFIX = "session_memory"
_DEFAULT_TTL_SECONDS = 3600


def _redis_key(session_id: str, key: str) -> str:
    return f"{_KEY_PREFIX}:{session_id}:{key}"


def set_session_value(session_id: str, key: str, value: Any, *, ttl_seconds: int = _DEFAULT_TTL_SECONDS) -> bool:
    """Stores a JSON-serializable value scoped to a session. Returns
    whether the write actually happened -- False when Redis is disabled or
    unreachable, fail-open, matching rate_limit.py's own contract."""
    if not get_settings().REDIS_URL:
        return False
    try:
        get_redis_client().set(_redis_key(session_id, key), json.dumps(value), ex=ttl_seconds)
        return True
    except Exception as e:
        logger.warning("Session memory write skipped (%s)", e)
        return False


def get_session_value(session_id: str, key: str) -> Optional[Any]:
    if not get_settings().REDIS_URL:
        return None
    try:
        raw = get_redis_client().get(_redis_key(session_id, key))
        return json.loads(raw) if raw is not None else None
    except Exception as e:
        logger.warning("Session memory read skipped (%s)", e)
        return None


def append_session_turn(session_id: str, role: str, content: str, *,
                        max_turns: int = 20, ttl_seconds: int = _DEFAULT_TTL_SECONDS) -> None:
    """The "last N chat turns" case from docs/v2/AGENTS.md's memory table --
    appends one {role, content} turn to a bounded, TTL-refreshed list. No
    current caller yet (chatbot.py's /api/ask is still single-turn) -- this
    is the infrastructure a future multi-turn session would consume, built
    now because it needed nothing this environment lacks, not because a
    consumer already exists."""
    turns = get_session_value(session_id, "turns") or []
    turns.append({"role": role, "content": content})
    turns = turns[-max_turns:]
    set_session_value(session_id, "turns", turns, ttl_seconds=ttl_seconds)


def get_session_turns(session_id: str) -> List[dict]:
    return get_session_value(session_id, "turns") or []


def clear_session(session_id: str) -> bool:
    if not get_settings().REDIS_URL:
        return False
    try:
        client = get_redis_client()
        keys = list(client.scan_iter(match=f"{_KEY_PREFIX}:{session_id}:*"))
        if keys:
            client.delete(*keys)
        return True
    except Exception as e:
        logger.warning("Session memory clear skipped (%s)", e)
        return False
