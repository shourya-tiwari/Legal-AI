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


# --------------------------------------------------------------------------
# Per-key RBAC (app/guard.py::require_role, docs/v2/ARCHITECTURE.md item 5)
# --------------------------------------------------------------------------

def test_create_api_key_defaults_to_admin_role(db_session):
    from app.db_models import ApiKey, Organization

    org = Organization(name="role-default-org")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)

    raw_key = create_api_key(db_session, org, "a-key")
    row = db_session.query(ApiKey).filter_by(key_hash=hash_api_key(raw_key)).first()
    assert row.role == "admin"


def test_create_api_key_rejects_an_invalid_role(db_session):
    from app.db_models import Organization

    org = Organization(name="role-invalid-org")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)

    with pytest.raises(ValueError):
        create_api_key(db_session, org, "a-key", role="superuser")


def test_get_current_org_carries_the_keys_role_and_id(monkeypatch, db_session):
    from app.auth import get_current_org
    from app.db_models import ApiKey, Organization

    monkeypatch.setattr(get_settings(), "AUTH_REQUIRED", True)

    org = Organization(name="role-carry-org")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    raw_key = create_api_key(db_session, org, "viewer-key", role="viewer")
    key_row = db_session.query(ApiKey).filter_by(key_hash=hash_api_key(raw_key)).first()

    ctx = get_current_org(authorization=f"Bearer {raw_key}", db=db_session)
    assert ctx.role == "viewer"
    assert ctx.api_key_id == key_row.id


def test_api_guard_attributes_the_audit_row_to_the_calling_key(client, db_session, monkeypatch):
    from app.db_models import AuditLog, Organization

    monkeypatch.setattr(get_settings(), "AUTH_REQUIRED", True)
    org = Organization(name="actor-id-org")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    raw_key = create_api_key(db_session, org, "actor-key")
    key_row = db_session.query(ApiKey).filter_by(key_hash=hash_api_key(raw_key)).first()

    resp = client.post(
        "/api/risk/scan", json={"text": "The Tenant shall indemnify the Landlord."},
        headers={"Authorization": f"Bearer {raw_key}"},
    )
    assert resp.status_code == 200

    row = db_session.query(AuditLog).filter_by(actor_id=key_row.id).order_by(AuditLog.id.desc()).first()
    assert row is not None
    assert row.org_id == org.id


def test_default_org_context_is_always_admin_role():
    from app.auth import get_current_org
    from app.db import SessionLocal

    assert get_settings().AUTH_REQUIRED is False  # the suite's default posture
    db = SessionLocal()
    try:
        ctx = get_current_org(authorization=None, db=db)
        assert ctx.role == "admin"
        assert ctx.api_key_id is None
    finally:
        db.close()
