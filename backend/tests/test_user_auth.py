"""
Per-user identity (docs/v2/ARCHITECTURE.md security item 5, `LEARNING_LOG.md`
#37): password hashing, login/session lifecycle, and the admin-only user
management routes -- the remaining half of Phase 7 RBAC after per-key roles
(`LEARNING_LOG.md` #36).
"""
from __future__ import annotations

import datetime

import pytest

from app.auth import (
    authenticate_user,
    create_session,
    create_user,
    generate_session_token,
    hash_password,
    hash_session_token,
    revoke_session,
    verify_password,
)
from app.config import get_settings
from app.db_models import Organization, Session as SessionRow, User


@pytest.fixture
def org(db_session, request):
    # A unique name per test -- the suite shares one in-memory DB across all
    # tests in a run, and organizations.name is unique (LEARNING_LOG.md #30's
    # shared-test-DB hazard).
    o = Organization(name=f"user-auth-test-org-{request.node.name}")
    db_session.add(o)
    db_session.commit()
    db_session.refresh(o)
    return o


# --------------------------------------------------------------------------
# password hashing
# --------------------------------------------------------------------------

def test_hash_password_round_trips():
    stored = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", stored) is True


def test_verify_password_rejects_a_wrong_password():
    stored = hash_password("correct horse battery staple")
    assert verify_password("wrong password", stored) is False


def test_hash_password_is_salted_so_two_hashes_of_the_same_password_differ():
    a = hash_password("same password")
    b = hash_password("same password")
    assert a != b
    assert verify_password("same password", a)
    assert verify_password("same password", b)


def test_verify_password_handles_a_malformed_stored_hash_gracefully():
    assert verify_password("anything", "not-a-real-hash") is False


# --------------------------------------------------------------------------
# create_user / authenticate_user
# --------------------------------------------------------------------------

def test_create_user_rejects_an_invalid_role(db_session, org):
    with pytest.raises(ValueError):
        create_user(db_session, org, "a@example.com", "password123", role="superuser")


def test_create_user_rejects_a_duplicate_email(db_session, org):
    create_user(db_session, org, "dup@example.com", "password123")
    with pytest.raises(ValueError):
        create_user(db_session, org, "dup@example.com", "password456")


def test_authenticate_user_succeeds_with_correct_credentials(db_session, org):
    create_user(db_session, org, "ok@example.com", "password123", role="editor")
    user = authenticate_user(db_session, "ok@example.com", "password123")
    assert user is not None
    assert user.role == "editor"


def test_authenticate_user_fails_with_wrong_password(db_session, org):
    create_user(db_session, org, "ok2@example.com", "password123")
    assert authenticate_user(db_session, "ok2@example.com", "wrong") is None


def test_authenticate_user_fails_for_unknown_email(db_session, org):
    assert authenticate_user(db_session, "nobody@example.com", "whatever") is None


def test_authenticate_user_fails_for_a_revoked_user(db_session, org):
    user = create_user(db_session, org, "revoked@example.com", "password123")
    user.revoked_at = datetime.datetime.now(datetime.timezone.utc)
    db_session.commit()
    assert authenticate_user(db_session, "revoked@example.com", "password123") is None


# --------------------------------------------------------------------------
# sessions
# --------------------------------------------------------------------------

def test_create_session_then_get_current_org_resolves_the_user(db_session, org, monkeypatch):
    from app.auth import get_current_org

    monkeypatch.setattr(get_settings(), "AUTH_REQUIRED", True)
    user = create_user(db_session, org, "session@example.com", "password123", role="viewer")
    token = create_session(db_session, user)

    ctx = get_current_org(authorization=f"Bearer {token}", db=db_session)
    assert ctx.role == "viewer"
    assert ctx.user_id == user.id
    assert ctx.user_email == "session@example.com"
    assert ctx.api_key_id is None


def test_expired_session_is_rejected(db_session, org, monkeypatch):
    from app.auth import get_current_org

    monkeypatch.setattr(get_settings(), "AUTH_REQUIRED", True)
    user = create_user(db_session, org, "expired@example.com", "password123")
    raw_token = generate_session_token()
    db_session.add(SessionRow(
        user_id=user.id, token_hash=hash_session_token(raw_token),
        expires_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1),
    ))
    db_session.commit()

    with pytest.raises(Exception) as exc:
        get_current_org(authorization=f"Bearer {raw_token}", db=db_session)
    assert "401" in str(exc.value) or getattr(exc.value, "status_code", None) == 401


def test_revoke_session_invalidates_the_token(db_session, org, monkeypatch):
    from app.auth import get_current_org

    monkeypatch.setattr(get_settings(), "AUTH_REQUIRED", True)
    user = create_user(db_session, org, "revoke-session@example.com", "password123")
    token = create_session(db_session, user)

    assert revoke_session(db_session, token) is True
    with pytest.raises(Exception):
        get_current_org(authorization=f"Bearer {token}", db=db_session)

    # revoking an already-revoked (or unknown) token reports False, not an error
    assert revoke_session(db_session, token) is False


# --------------------------------------------------------------------------
# routes
# --------------------------------------------------------------------------

def test_login_route_succeeds_and_returns_a_usable_token(client, db_session, org, monkeypatch):
    monkeypatch.setattr(get_settings(), "AUTH_REQUIRED", True)
    create_user(db_session, org, "route@example.com", "password123", role="admin")

    resp = client.post("/api/auth/login", json={"email": "route@example.com", "password": "password123"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["role"] == "admin"
    assert body["org_name"] == org.name

    # the returned token actually authenticates a subsequent request
    resp2 = client.post(
        "/api/risk/scan", json={"text": "The Tenant shall indemnify the Landlord."},
        headers={"Authorization": f"Bearer {body['token']}"},
    )
    assert resp2.status_code == 200


def test_login_route_rejects_wrong_password(client, db_session, org, monkeypatch):
    monkeypatch.setattr(get_settings(), "AUTH_REQUIRED", True)
    create_user(db_session, org, "route2@example.com", "password123")

    resp = client.post("/api/auth/login", json={"email": "route2@example.com", "password": "nope"})
    assert resp.status_code == 401


def test_user_management_routes_require_admin_role(client, db_session, org, monkeypatch):
    monkeypatch.setattr(get_settings(), "AUTH_REQUIRED", True)
    from app.auth import create_api_key

    viewer_key = create_api_key(db_session, org, "viewer-key", role="viewer")
    admin_key = create_api_key(db_session, org, "admin-key", role="admin")

    denied = client.post(
        "/api/auth/users", json={"email": "new@example.com", "password": "password123", "role": "editor"},
        headers={"Authorization": f"Bearer {viewer_key}"},
    )
    assert denied.status_code == 403

    created = client.post(
        "/api/auth/users", json={"email": "new@example.com", "password": "password123", "role": "editor"},
        headers={"Authorization": f"Bearer {admin_key}"},
    )
    assert created.status_code == 200
    assert created.json()["role"] == "editor"

    listed = client.get("/api/auth/users", headers={"Authorization": f"Bearer {admin_key}"})
    assert listed.status_code == 200
    assert any(u["email"] == "new@example.com" for u in listed.json()["users"])

    user_id = created.json()["id"]
    revoked = client.post(f"/api/auth/users/{user_id}/revoke", headers={"Authorization": f"Bearer {admin_key}"})
    assert revoked.status_code == 200
    assert revoked.json()["revoked_at"] is not None

    # the revoked user can no longer log in
    login_after_revoke = client.post("/api/auth/login", json={"email": "new@example.com", "password": "password123"})
    assert login_after_revoke.status_code == 401


def test_logout_revokes_the_current_session(client, db_session, org, monkeypatch):
    monkeypatch.setattr(get_settings(), "AUTH_REQUIRED", True)
    create_user(db_session, org, "logout@example.com", "password123")

    token = client.post(
        "/api/auth/login", json={"email": "logout@example.com", "password": "password123"},
    ).json()["token"]

    resp = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["revoked"] is True

    # the same token no longer authenticates
    resp2 = client.post(
        "/api/risk/scan", json={"text": "x"}, headers={"Authorization": f"Bearer {token}"},
    )
    assert resp2.status_code == 401


def test_logout_rejects_an_api_key_credential(client, db_session, org, monkeypatch):
    from app.auth import create_api_key

    monkeypatch.setattr(get_settings(), "AUTH_REQUIRED", True)
    api_key = create_api_key(db_session, org, "not-a-session")

    resp = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {api_key}"})
    assert resp.status_code == 400


def test_audit_log_attributes_a_user_authenticated_request_as_user(client, db_session, org, monkeypatch):
    from app.db_models import AuditLog

    monkeypatch.setattr(get_settings(), "AUTH_REQUIRED", True)
    user = create_user(db_session, org, "attribution@example.com", "password123")
    token = create_session(db_session, user)

    resp = client.post(
        "/api/risk/scan", json={"text": "The Tenant shall indemnify the Landlord."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    row = (
        db_session.query(AuditLog)
        .filter_by(actor_id=user.id, actor_type="user")
        .order_by(AuditLog.id.desc()).first()
    )
    assert row is not None
    assert row.org_id == org.id
