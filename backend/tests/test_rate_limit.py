"""
Unit tests for the rate limiter itself (no real Redis needed): a fake client
exercises the counting/limit logic, and a broken client proves the fail-open
behavior that keeps the API available if Redis goes down.
"""
import pytest

from app.config import get_settings
from app.rate_limit import RateLimitExceeded, check_rate_limit


class _FakeRedis:
    def __init__(self):
        self.counts = {}

    def incr(self, key):
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    def expire(self, key, seconds):
        pass


class _BrokenRedis:
    def incr(self, key):
        raise ConnectionError("redis is down")


def test_disabled_when_redis_url_empty(monkeypatch):
    monkeypatch.setattr(get_settings(), "REDIS_URL", "")
    # Should not raise even after many calls, since it's a no-op.
    for _ in range(1000):
        check_rate_limit("some-key")


def test_allows_requests_under_the_limit(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(get_settings(), "REDIS_URL", "redis://placeholder/0")
    monkeypatch.setattr(get_settings(), "RATE_LIMIT_PER_MINUTE", 5)
    monkeypatch.setattr("app.rate_limit.get_redis_client", lambda: fake)

    for _ in range(5):
        check_rate_limit("client-a")


def test_blocks_requests_over_the_limit(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(get_settings(), "REDIS_URL", "redis://placeholder/0")
    monkeypatch.setattr(get_settings(), "RATE_LIMIT_PER_MINUTE", 3)
    monkeypatch.setattr("app.rate_limit.get_redis_client", lambda: fake)

    for _ in range(3):
        check_rate_limit("client-b")
    with pytest.raises(RateLimitExceeded):
        check_rate_limit("client-b")


def test_fails_open_when_redis_is_unreachable(monkeypatch):
    monkeypatch.setattr(get_settings(), "REDIS_URL", "redis://placeholder/0")
    monkeypatch.setattr("app.rate_limit.get_redis_client", lambda: _BrokenRedis())

    # Should not raise RateLimitExceeded (or anything else) despite the
    # backing store being down.
    check_rate_limit("client-c")
