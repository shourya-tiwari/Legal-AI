import os

# Must be set before any module imports app.config.get_settings() for the
# first time (e.g. app.main, app.services.genai_client), so the Settings()
# singleton never sees a missing GOOGLE_API_KEY during tests, and the DB/auth
# layer uses an isolated in-memory database instead of a real Postgres.
os.environ.setdefault("GOOGLE_API_KEY", "test-dummy-key")
os.environ.setdefault("GENAI_MODEL", "gemini-flash-latest")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "")  # rate limiting disabled in tests; see test_rate_limit.py for its own coverage
os.environ.setdefault("AUTH_REQUIRED", "false")

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    # Context-manager form so FastAPI's startup event (init_db()) runs.
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db_session(client):
    """A session on the same (in-memory) engine the app under test uses,
    for tests that need to set up or inspect rows directly."""
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
