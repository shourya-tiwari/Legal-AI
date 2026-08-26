import os

# Must be set before any module imports app.config.get_settings() for the
# first time (e.g. app.main, app.services.genai_client), so the Settings()
# singleton never sees a missing GOOGLE_API_KEY during tests.
os.environ.setdefault("GOOGLE_API_KEY", "test-dummy-key")
os.environ.setdefault("GENAI_MODEL", "gemini-flash-latest")

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)
