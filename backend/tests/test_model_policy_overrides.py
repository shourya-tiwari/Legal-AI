"""
Admin-settable Class C toggles (app/services/model_router/overrides.py,
docs/v2/ROADMAP.md Phase 7 "Provider & Model admin: per-task/tier Class C
toggles") and the delta-report/latency additions to routes/models.py.
"""
from __future__ import annotations

from app.config import get_settings
from app.services.model_router import overrides
from app.services.model_router.policy import get_policy
from app.services.model_router.router import get_router


def teardown_function(_fn):
    # Clearing the cache alone isn't enough -- these tests share the
    # session's in-memory DB (LEARNING_LOG.md #30's standing hazard), so an
    # override row left behind would keep being reloaded into the cache by
    # every later test in the whole suite, not just this file.
    for task in ("qa", "summarize"):
        overrides.clear_class_c_override(task)
    overrides.get_class_c_overrides.cache_clear()


# --------------------------------------------------------------------------
# overrides module
# --------------------------------------------------------------------------

def test_no_override_by_default(db_session):
    # db_session (unused directly) ensures init_db() has run -- this is the
    # only test in the file that doesn't otherwise touch the DB, and this
    # file's teardown_function always does.
    overrides.get_class_c_overrides.cache_clear()
    assert overrides.is_class_c_disabled_for_task("qa") is False


def test_set_and_read_an_override(db_session):
    overrides.set_class_c_override("qa", True, reason="cost control")
    assert overrides.is_class_c_disabled_for_task("qa") is True

    all_overrides = overrides.get_class_c_overrides()
    assert all_overrides["qa"] is True


def test_clear_override_reverts_to_default(db_session):
    overrides.set_class_c_override("qa", True)
    assert overrides.clear_class_c_override("qa") is True
    assert overrides.is_class_c_disabled_for_task("qa") is False


def test_clear_a_nonexistent_override_reports_false(db_session):
    assert overrides.clear_class_c_override("nonexistent-task") is False


# --------------------------------------------------------------------------
# router-level: the override can only remove a Class C candidate, never add one
# --------------------------------------------------------------------------

def test_override_removes_class_c_from_the_resolved_chain(monkeypatch, db_session):
    monkeypatch.setenv("EXTERNAL_PROVIDERS_ENABLED", "true")
    get_settings.cache_clear(); get_policy.cache_clear(); get_router.cache_clear()

    from app.services.model_router import get_registry
    from app.services.model_router.types import SensitivityTier

    if "gemini" not in get_registry():
        import pytest
        pytest.skip("providers-external not installed in this environment")

    router = get_router()
    before = router._resolve_chain("qa", "generate", SensitivityTier.PUBLIC)
    assert any(p.name == "gemini" for p in before)

    overrides.set_class_c_override("qa", True, reason="test")
    after = router._resolve_chain("qa", "generate", SensitivityTier.PUBLIC)
    assert not any(p.name == "gemini" for p in after)
    # every Class B candidate the static policy already had stays present
    assert [p.name for p in after] == [p.name for p in before if p.name != "gemini"]


# --------------------------------------------------------------------------
# routes
# --------------------------------------------------------------------------

def test_class_c_override_routes_require_admin_and_round_trip(client, db_session, monkeypatch):
    from app.auth import create_api_key
    from app.db_models import Organization

    monkeypatch.setattr(get_settings(), "AUTH_REQUIRED", True)
    org = Organization(name="override-route-test-org")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    viewer_key = create_api_key(db_session, org, "viewer-key", role="viewer")
    admin_key = create_api_key(db_session, org, "admin-key", role="admin")

    denied = client.put("/api/models/class-c-overrides/summarize", json={"class_c_disabled": True},
                        headers={"Authorization": f"Bearer {viewer_key}"})
    assert denied.status_code == 403

    set_resp = client.put("/api/models/class-c-overrides/summarize",
                          json={"class_c_disabled": True, "reason": "cost control"},
                          headers={"Authorization": f"Bearer {admin_key}"})
    assert set_resp.status_code == 200
    assert set_resp.json() == {"task": "summarize", "class_c_disabled": True, "reason": "cost control",
                               "updated_at": set_resp.json()["updated_at"]}

    listed = client.get("/api/models/class-c-overrides", headers={"Authorization": f"Bearer {admin_key}"})
    assert any(o["task"] == "summarize" for o in listed.json()["overrides"])

    cleared = client.delete("/api/models/class-c-overrides/summarize", headers={"Authorization": f"Bearer {admin_key}"})
    assert cleared.status_code == 200

    not_found = client.delete("/api/models/class-c-overrides/summarize", headers={"Authorization": f"Bearer {admin_key}"})
    assert not_found.status_code == 404


def test_delta_report_route_requires_admin_and_calls_build_report(client, db_session, monkeypatch):
    from app.auth import create_api_key
    from app.db_models import Organization

    monkeypatch.setattr(get_settings(), "AUTH_REQUIRED", True)
    org = Organization(name="delta-report-route-test-org")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    viewer_key = create_api_key(db_session, org, "viewer-key", role="viewer")
    admin_key = create_api_key(db_session, org, "admin-key", role="admin")

    denied = client.post("/api/models/delta-report", headers={"Authorization": f"Bearer {viewer_key}"})
    assert denied.status_code == 403

    from app.eval.delta_report import Row

    fake_rows = [Row(task="qa", local_ms=None, external_ms=None, local_len=0, external_len=0,
                     agreement_f1=0.0, local_error="local-llm: not available",
                     external_error="gemini: not available")]
    # build_report is imported lazily inside run_delta_report, so the patch
    # target is the real module it's imported from.
    monkeypatch.setattr("app.eval.delta_report.build_report", lambda: fake_rows)

    resp = client.post("/api/models/delta-report", headers={"Authorization": f"Bearer {admin_key}"})
    assert resp.status_code == 200
    assert resp.json()["rows"][0]["task"] == "qa"


def test_models_status_surfaces_recent_latency(client, db_session):
    # ModelProviderStatus.name is the registry alias ("local-embed-hash"),
    # not the provider's own name ("hashing-embed") -- model_calls.provider
    # is always the latter (RoutingDecision.provider in router.py), which is
    # exactly the distinction _recent_latency's own docstring calls out.
    from app.db_models import ModelCall

    db_session.add(ModelCall(task="embed_corpus", capability="embed", sensitivity="internal",
                             provider="hashing-embed", model="hashing-384d", hosting_class="A",
                             reason="primary", latency_ms=42, ok=True))
    db_session.commit()

    resp = client.get("/api/models/status")
    assert resp.status_code == 200
    hashing = next(p for p in resp.json()["providers"] if p["name"] == "local-embed-hash")
    assert hashing["recent_call_count"] >= 1
    assert hashing["recent_avg_latency_ms"] is not None
