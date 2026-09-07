"""
Per-org feature flags + webhook notifications (app/services/org_settings.py,
app/routes/org_settings.py, docs/v2/ROADMAP.md Phase 7).
"""
from __future__ import annotations

from app.config import get_settings
from app.db_models import Organization
from app.services.org_settings import is_feature_enabled, notify_org, send_webhook_notification


# --------------------------------------------------------------------------
# is_feature_enabled
# --------------------------------------------------------------------------

def test_unset_flag_falls_back_to_its_known_default():
    org = Organization(name="x", feature_flags={})
    assert is_feature_enabled(org, "api_v2_enabled") is True  # the one real flag's default


def test_explicit_false_overrides_the_default():
    org = Organization(name="x", feature_flags={"api_v2_enabled": False})
    assert is_feature_enabled(org, "api_v2_enabled") is False


def test_an_unknown_flag_defaults_to_true():
    org = Organization(name="x", feature_flags={})
    assert is_feature_enabled(org, "some_future_flag") is True


def test_none_feature_flags_does_not_raise():
    org = Organization(name="x", feature_flags=None)
    assert is_feature_enabled(org, "api_v2_enabled") is True


# --------------------------------------------------------------------------
# webhook notification -- mocked requests.post
# --------------------------------------------------------------------------

def test_send_webhook_notification_success(monkeypatch):
    calls = []

    class _Resp:
        def raise_for_status(self):
            pass

    def fake_post(url, json=None, timeout=None):
        calls.append((url, json, timeout))
        return _Resp()

    monkeypatch.setattr("app.services.org_settings.requests.post", fake_post)

    ok = send_webhook_notification("https://example.com/hook", "analysis.completed", {"document_id": 1})
    assert ok is True
    assert calls[0][0] == "https://example.com/hook"
    assert calls[0][1] == {"event": "analysis.completed", "data": {"document_id": 1}}


def test_send_webhook_notification_fails_soft_on_error(monkeypatch):
    def fake_post(*a, **k):
        raise ConnectionError("no route to host")

    monkeypatch.setattr("app.services.org_settings.requests.post", fake_post)

    ok = send_webhook_notification("https://example.com/hook", "analysis.completed", {})
    assert ok is False  # never raises


def test_notify_org_noops_when_no_webhook_configured(monkeypatch):
    called = {"hit": False}
    monkeypatch.setattr("app.services.org_settings.send_webhook_notification",
                        lambda *a, **k: called.update(hit=True))

    org = Organization(name="x", webhook_url=None)
    notify_org(org, "analysis.completed", {})
    assert called["hit"] is False


def test_notify_org_calls_send_when_webhook_is_set(monkeypatch):
    captured = {}
    monkeypatch.setattr("app.services.org_settings.send_webhook_notification",
                        lambda url, event, payload: captured.update(url=url, event=event, payload=payload))

    org = Organization(name="x", webhook_url="https://example.com/hook")
    notify_org(org, "analysis.completed", {"document_id": 5})
    assert captured == {"url": "https://example.com/hook", "event": "analysis.completed",
                        "payload": {"document_id": 5}}


# --------------------------------------------------------------------------
# routes
# --------------------------------------------------------------------------

def test_org_settings_round_trip_and_admin_only_write(client, db_session, monkeypatch):
    from app.auth import create_api_key

    monkeypatch.setattr(get_settings(), "AUTH_REQUIRED", True)
    org = Organization(name="org-settings-route-test-org")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    viewer_key = create_api_key(db_session, org, "viewer-key", role="viewer")
    admin_key = create_api_key(db_session, org, "admin-key", role="admin")

    # viewer can read
    read_resp = client.get("/api/org/settings", headers={"Authorization": f"Bearer {viewer_key}"})
    assert read_resp.status_code == 200
    assert read_resp.json()["feature_flags"] == {}
    assert read_resp.json()["webhook_url"] is None

    # viewer cannot write
    denied = client.put("/api/org/settings", json={"webhook_url": "https://example.com/hook"},
                        headers={"Authorization": f"Bearer {viewer_key}"})
    assert denied.status_code == 403

    # admin can write, and flags are merged not replaced
    set1 = client.put("/api/org/settings", json={"feature_flags": {"api_v2_enabled": False}},
                      headers={"Authorization": f"Bearer {admin_key}"})
    assert set1.status_code == 200
    assert set1.json()["feature_flags"] == {"api_v2_enabled": False}

    set2 = client.put("/api/org/settings",
                      json={"feature_flags": {"some_other_flag": True}, "webhook_url": "https://example.com/hook"},
                      headers={"Authorization": f"Bearer {admin_key}"})
    assert set2.status_code == 200
    assert set2.json()["feature_flags"] == {"api_v2_enabled": False, "some_other_flag": True}
    assert set2.json()["webhook_url"] == "https://example.com/hook"

    # empty string clears the webhook
    cleared = client.put("/api/org/settings", json={"webhook_url": ""},
                         headers={"Authorization": f"Bearer {admin_key}"})
    assert cleared.json()["webhook_url"] is None


def test_disabling_api_v2_enabled_blocks_v2_routes(client, db_session, monkeypatch):
    from app.auth import create_api_key

    monkeypatch.setattr(get_settings(), "AUTH_REQUIRED", True)
    org = Organization(name="feature-flag-block-test-org")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    admin_key = create_api_key(db_session, org, "admin-key", role="admin")

    upload_resp = client.post("/api/upload", files={"file": ("q.txt", b"Some contract text.", "text/plain")},
                              headers={"Authorization": f"Bearer {admin_key}"})
    document_id = upload_resp.json()["document_id"]

    # v2 works before disabling
    before = client.get(f"/api/v2/documents/{document_id}", headers={"Authorization": f"Bearer {admin_key}"})
    assert before.status_code == 200

    client.put("/api/org/settings", json={"feature_flags": {"api_v2_enabled": False}},
              headers={"Authorization": f"Bearer {admin_key}"})

    after = client.get(f"/api/v2/documents/{document_id}", headers={"Authorization": f"Bearer {admin_key}"})
    assert after.status_code == 403

    # V1 endpoints are untouched by the flag
    v1_resp = client.post("/api/risk/scan", json={"text": "The Tenant shall indemnify the Landlord."},
                          headers={"Authorization": f"Bearer {admin_key}"})
    assert v1_resp.status_code == 200


def test_analyze_fires_a_webhook_when_one_is_configured(client, db_session, monkeypatch):
    from app.auth import create_api_key

    monkeypatch.setattr(get_settings(), "AUTH_REQUIRED", True)
    org = Organization(name="webhook-fire-test-org", webhook_url="https://example.com/hook")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    admin_key = create_api_key(db_session, org, "admin-key", role="admin")

    from types import SimpleNamespace

    captured = {}
    monkeypatch.setattr("app.routes.agents.notify_org",
                        lambda organization, event, payload: captured.update(
                            org_id=organization.id, event=event, payload=payload))
    # "indemnify" is a risk keyword -> the planner includes summarize, which
    # calls generate_content for real unless mocked, same as
    # test_routes.py::test_agents_analyze_endpoint.
    monkeypatch.setattr("app.agents.summary.generate_content", lambda *a, **k: "Risk summary, no citations.")
    monkeypatch.setattr(
        "app.services.contextualizer.rag.embed_content",
        lambda contents, model=None: SimpleNamespace(
            embeddings=[SimpleNamespace(values=[0.1, 0.2, 0.3]) for _ in contents]),
    )
    import app.services.rag.hybrid as hybrid_module
    hybrid_module._dense_index = None

    upload_resp = client.post(
        "/api/upload",
        files={"file": ("q.txt", b'The Tenant ("Tenant") shall indemnify the Landlord.', "text/plain")},
        headers={"Authorization": f"Bearer {admin_key}"},
    )
    document_id = upload_resp.json()["document_id"]

    resp = client.post("/api/agents/analyze", json={"document_id": document_id},
                       headers={"Authorization": f"Bearer {admin_key}"})
    assert resp.status_code == 200

    # BackgroundTasks run after the response within TestClient's request cycle
    assert captured.get("event") == "analysis.completed"
    assert captured.get("org_id") == org.id
    assert captured["payload"]["document_id"] == document_id
