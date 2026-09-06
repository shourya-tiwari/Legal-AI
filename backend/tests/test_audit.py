"""
Egress audit log route (app/routes/audit.py, docs/v2/ARCHITECTURE.md item 2
"log every byte sent" + item 9 "audit trail"). `record_egress` (app/services/
model_router/telemetry.py) has been covered at the router level in
test_model_router.py; this covers the read side.
"""
from __future__ import annotations

import json

from app.auth import get_or_create_default_org
from app.db_models import AuditLog


def test_egress_log_lists_rows_newest_first(client, db_session):
    org = get_or_create_default_org(db_session)
    db_session.add(AuditLog(
        org_id=org.id, action="model_egress", resource="qa", egress_target="gemini",
        detail=json.dumps({
            "model": "gemini-x", "sensitivity": "public", "policy_version": 2,
            "payload_sha256": "abc123", "redacted_categories": {"email": 1},
        }),
    ))
    db_session.commit()

    resp = client.get("/api/audit/egress")
    assert resp.status_code == 200
    entries = resp.json()["entries"]
    entry = next(e for e in entries if e["provider"] == "gemini" and e["task"] == "qa")
    assert entry["model"] == "gemini-x"
    assert entry["sensitivity"] == "public"
    assert entry["policy_version"] == 2
    assert entry["payload_sha256"] == "abc123"
    assert entry["redacted_categories"] == {"email": 1}


def test_egress_log_ignores_non_egress_audit_rows(client, db_session):
    org = get_or_create_default_org(db_session)
    before = len(client.get("/api/audit/egress").json()["entries"])

    db_session.add(AuditLog(org_id=org.id, action="GET", resource="/api/upload"))
    db_session.commit()

    after = len(client.get("/api/audit/egress").json()["entries"])
    assert after == before


def test_egress_log_respects_limit(client, db_session):
    org = get_or_create_default_org(db_session)
    for i in range(5):
        db_session.add(AuditLog(org_id=org.id, action="model_egress", resource="qa",
                                egress_target="gemini", detail=json.dumps({"redacted_categories": {}})))
    db_session.commit()

    resp = client.get("/api/audit/egress", params={"limit": 2})
    assert resp.status_code == 200
    assert len(resp.json()["entries"]) == 2
