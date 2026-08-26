"""
Tests for the Phase 1 auth layer: default-org resolution when AUTH_REQUIRED
is off, and API-key enforcement when it's on.
"""
import pytest

from app.auth import create_api_key, get_or_create_default_org, hash_api_key
from app.config import get_settings
from app.db_models import ApiKey, Organization


def test_upload_resolves_to_default_org_when_auth_not_required(client):
    files = {"file": ("a.txt", b"Hello world.", "text/plain")}
    resp = client.post("/api/upload", files=files)

    assert resp.status_code == 200
    assert resp.json()["document_id"] is not None


def test_endpoint_rejects_missing_key_when_auth_required(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "AUTH_REQUIRED", True)

    resp = client.post("/api/risk/scan", json={"text": "The Tenant shall indemnify the Landlord."})

    assert resp.status_code == 401


def test_endpoint_rejects_invalid_key_when_auth_required(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "AUTH_REQUIRED", True)

    resp = client.post(
        "/api/risk/scan",
        json={"text": "The Tenant shall indemnify the Landlord."},
        headers={"Authorization": "Bearer not-a-real-key"},
    )

    assert resp.status_code == 401


def test_endpoint_accepts_valid_api_key_when_auth_required(client, monkeypatch, db_session):
    monkeypatch.setattr(get_settings(), "AUTH_REQUIRED", True)

    org = Organization(name="acme-test")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    raw_key = create_api_key(db_session, org, "test-key")

    resp = client.post(
        "/api/risk/scan",
        json={"text": "The Tenant shall indemnify the Landlord."},
        headers={"Authorization": f"Bearer {raw_key}"},
    )

    assert resp.status_code == 200


def test_hash_api_key_is_deterministic_and_not_reversible():
    h1 = hash_api_key("secret-key")
    h2 = hash_api_key("secret-key")
    assert h1 == h2
    assert h1 != "secret-key"
