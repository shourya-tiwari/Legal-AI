"""
Session-tier memory (app/services/memory/session.py, docs/v2/AGENTS.md's
Memory system, Phase 7). Fake-Redis unit tests mirror test_rate_limit.py's
pattern (no real Redis needed for the fail-open/logic checks); a real-Redis
test runs when REDIS_TEST_URL is set, proving the actual round trip against
a live server, not just the mocked logic.
"""
from __future__ import annotations

import os

import pytest

from app.config import get_settings
from app.services.memory import session


class _FakeRedis:
    def __init__(self):
        self.store = {}

    def set(self, key, value, ex=None):
        self.store[key] = value

    def get(self, key):
        return self.store.get(key)

    def scan_iter(self, match=None):
        prefix = match.rstrip("*") if match else ""
        return [k for k in self.store if k.startswith(prefix)]

    def delete(self, *keys):
        for k in keys:
            self.store.pop(k, None)


class _BrokenRedis:
    def set(self, *a, **k):
        raise ConnectionError("redis is down")

    def get(self, *a, **k):
        raise ConnectionError("redis is down")


def test_disabled_when_redis_url_empty(monkeypatch):
    monkeypatch.setattr(get_settings(), "REDIS_URL", "")
    assert session.set_session_value("s1", "k", "v") is False
    assert session.get_session_value("s1", "k") is None


def test_set_and_get_round_trip_with_a_fake_client(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(get_settings(), "REDIS_URL", "redis://placeholder/0")
    monkeypatch.setattr("app.services.memory.session.get_redis_client", lambda: fake)

    assert session.set_session_value("s1", "role", "admin") is True
    assert session.get_session_value("s1", "role") == "admin"


def test_get_missing_key_returns_none(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(get_settings(), "REDIS_URL", "redis://placeholder/0")
    monkeypatch.setattr("app.services.memory.session.get_redis_client", lambda: fake)

    assert session.get_session_value("s1", "nope") is None


def test_append_session_turn_bounds_to_max_turns(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(get_settings(), "REDIS_URL", "redis://placeholder/0")
    monkeypatch.setattr("app.services.memory.session.get_redis_client", lambda: fake)

    for i in range(5):
        session.append_session_turn("s1", "user", f"turn {i}", max_turns=3)

    turns = session.get_session_turns("s1")
    assert len(turns) == 3
    assert [t["content"] for t in turns] == ["turn 2", "turn 3", "turn 4"]


def test_clear_session_removes_only_that_sessions_keys(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(get_settings(), "REDIS_URL", "redis://placeholder/0")
    monkeypatch.setattr("app.services.memory.session.get_redis_client", lambda: fake)

    session.set_session_value("s1", "a", 1)
    session.set_session_value("s2", "a", 1)

    assert session.clear_session("s1") is True
    assert session.get_session_value("s1", "a") is None
    assert session.get_session_value("s2", "a") == 1  # untouched


def test_fails_open_when_redis_is_unreachable(monkeypatch):
    monkeypatch.setattr(get_settings(), "REDIS_URL", "redis://placeholder/0")
    monkeypatch.setattr("app.services.memory.session.get_redis_client", lambda: _BrokenRedis())

    assert session.set_session_value("s1", "k", "v") is False
    assert session.get_session_value("s1", "k") is None


# --------------------------------------------------------------------------
# real Redis (opt-in via REDIS_TEST_URL) -- the actual round trip, not a mock
# --------------------------------------------------------------------------

_REAL_REDIS_URL = os.environ.get("REDIS_TEST_URL", "")


@pytest.mark.skipif(not _REAL_REDIS_URL, reason="REDIS_TEST_URL not set -- set it to run against a real Redis")
def test_session_memory_round_trips_against_a_real_redis(monkeypatch):
    import app.rate_limit as rate_limit_module

    monkeypatch.setattr(get_settings(), "REDIS_URL", _REAL_REDIS_URL)
    rate_limit_module.get_redis_client.cache_clear()

    session_id = "real-redis-integration-test-session"
    session.clear_session(session_id)
    try:
        assert session.get_session_turns(session_id) == []
        session.append_session_turn(session_id, "user", "What's the notice period?")
        session.append_session_turn(session_id, "assistant", "30 days.")
        turns = session.get_session_turns(session_id)
        assert turns == [
            {"role": "user", "content": "What's the notice period?"},
            {"role": "assistant", "content": "30 days."},
        ]
    finally:
        session.clear_session(session_id)
        rate_limit_module.get_redis_client.cache_clear()
