"""
/api/v2/* -- the document-first API surface. Each endpoint loads a persisted
document by id and calls the same service as its V1 counterpart, so the mocks
mirror test_routes.py (patched at the consumer module).
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from tests.test_routes import fake_embed_content, fake_generate_content

CONTRACT = (
    'This Agreement is made on January 1, 2025 between ABC Corp ("Company") and Jane Doe.\n\n'
    "The Tenant shall indemnify the Landlord for any damages.\n\n"
    "Either party may terminate this Agreement with 30 days written notice."
)


@pytest.fixture
def document_id(client):
    resp = client.post("/api/upload", files={"file": ("contract.txt", CONTRACT.encode(), "text/plain")})
    assert resp.status_code == 200
    return resp.json()["document_id"]


@pytest.fixture(autouse=True)
def _reset_dense_index():
    import app.services.rag.hybrid as hybrid_module
    hybrid_module._dense_index = None
    yield
    hybrid_module._dense_index = None


def test_get_document_returns_the_stored_record(client, document_id):
    resp = client.get(f"/api/v2/documents/{document_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["document_id"] == document_id
    assert "January 1, 2025" in body["full_text"]
    assert len(body["blocks"]) >= 1


def test_unknown_document_is_404(client):
    assert client.get("/api/v2/documents/999999").status_code == 404
    assert client.post("/api/v2/documents/999999/ask", json={"question": "?"}).status_code == 404


def test_v2_analyze_runs_the_planner(client, document_id, monkeypatch):
    monkeypatch.setattr("app.agents.summary.generate_content", lambda *a, **k: "Risk summary text.")
    monkeypatch.setattr("app.services.contextualizer.rag.embed_content", fake_embed_content)

    resp = client.post(f"/api/v2/documents/{document_id}/analyze", json={"analysis_mode": "full"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["document_id"] == document_id
    assert body["plan"][-1] == "verifier"
    assert "planner" in [s["agent_name"] for s in body["trace"]]
    # the contract has "indemnify" -> the planner runs risk_compliance
    assert "risk_compliance" in body["plan"]


def test_v2_analyze_risk_only_mode_prunes_the_plan(client, document_id):
    resp = client.post(f"/api/v2/documents/{document_id}/analyze", json={"analysis_mode": "risk_only"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["plan"] == ["risk_compliance", "verifier"]
    assert "research" not in body["plan"]


def test_v2_analyze_rejects_bad_mode(client, document_id):
    assert client.post(f"/api/v2/documents/{document_id}/analyze",
                       json={"analysis_mode": "everything"}).status_code == 422


def test_v2_rewrite_whole_document(client, document_id, monkeypatch):
    monkeypatch.setattr("app.services.rewriter.generate_content", fake_generate_content)
    resp = client.post(f"/api/v2/documents/{document_id}/rewrite", json={})
    assert resp.status_code == 200
    assert resp.json()["rewritten_text"]


def test_v2_rewrite_one_block(client, document_id, monkeypatch):
    monkeypatch.setattr("app.services.rewriter.generate_content", fake_generate_content)
    blocks = client.get(f"/api/v2/documents/{document_id}").json()["blocks"]
    resp = client.post(f"/api/v2/documents/{document_id}/rewrite", json={"block_id": blocks[0]["id"]})
    assert resp.status_code == 200


def test_v2_rewrite_unknown_block_is_404(client, document_id):
    assert client.post(f"/api/v2/documents/{document_id}/rewrite",
                       json={"block_id": "nope"}).status_code == 404


def test_v2_map(client, document_id, monkeypatch):
    monkeypatch.setattr("app.services.timeline.generate_content", fake_generate_content)
    resp = client.post(f"/api/v2/documents/{document_id}/map")
    assert resp.status_code == 200
    assert "structure" in resp.json()


def test_v2_ask(client, document_id, monkeypatch):
    monkeypatch.setattr("app.services.chatbot.generate_content", fake_generate_content)
    resp = client.post(f"/api/v2/documents/{document_id}/ask", json={"question": "How do I terminate?"})
    assert resp.status_code == 200
    assert resp.json()["answer"]


def test_v2_risk_scan(client, document_id, monkeypatch):
    monkeypatch.setattr("app.services.risk_radar.detector.generate_content", fake_generate_content)
    resp = client.post(f"/api/v2/documents/{document_id}/risk-scan", json={})
    assert resp.status_code == 200
    assert "flagged_clauses" in resp.json()


def test_v2_contextualize(client, document_id, monkeypatch):
    monkeypatch.setattr("app.services.contextualizer.explainer.generate_content", fake_generate_content)
    monkeypatch.setattr("app.services.contextualizer.rag.embed_content", fake_embed_content)
    blocks = client.get(f"/api/v2/documents/{document_id}").json()["blocks"]
    resp = client.post(
        f"/api/v2/documents/{document_id}/contextualize",
        json={"block_id": blocks[1]["id"],
              "context": {"role": "tenant", "location": "California", "contract_type": "lease", "tone": "plain"}},
    )
    assert resp.status_code == 200
    assert resp.json()["explanation"]


def test_v2_consistency_flags_a_conflict_against_another_document(client, document_id, monkeypatch):
    # fake_embed_content returns the same vector for every input, so every
    # deontic-tagged clause pair is "maximally similar" -- this test checks
    # the route wiring + real deontic tagging, not the similarity threshold
    # itself (see tests/test_consistency.py for that).
    monkeypatch.setattr("app.services.consistency.embed_content", fake_embed_content)

    other = client.post(
        "/api/upload",
        files={"file": ("other.txt", b"The Tenant shall not indemnify the Landlord for any damages.", "text/plain")},
    )
    assert other.status_code == 200

    resp = client.post(f"/api/v2/documents/{document_id}/consistency")
    assert resp.status_code == 200
    body = resp.json()
    assert body["document_id"] == document_id
    assert body["other_documents_checked"] >= 1
    assert any(f["is_conflict"] for f in body["findings"])


def test_v2_consistency_never_compares_a_document_against_itself(client, document_id, monkeypatch):
    # Every other test in this session uploads into the same shared default
    # org (AUTH_REQUIRED=false, in-memory SQLite shared across the whole
    # suite) -- so this can't assert an exact "no other documents" count.
    # What's guaranteed regardless of test order: document_id never shows up
    # as its own "other_document_id".
    monkeypatch.setattr("app.services.consistency.embed_content", fake_embed_content)
    resp = client.post(f"/api/v2/documents/{document_id}/consistency")
    assert resp.status_code == 200
    body = resp.json()
    assert all(f["other_document_id"] != document_id for f in body["findings"])


def test_v2_simulate_classifies_events_relative_to_a_reference_date(client, document_id):
    # CONTRACT has "January 1, 2025" -- from a 2025-06-01 vantage point that's past.
    resp = client.post(
        f"/api/v2/documents/{document_id}/simulate",
        json={"reference_date": "2025-06-01", "warning_window_days": 30},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["document_id"] == document_id
    assert body["reference_date"] == "2025-06-01"
    assert any(e["date"] == "2025-01-01" and e["status"] == "past" for e in body["events"])


def test_v2_simulate_defaults_to_today(client, document_id):
    resp = client.post(f"/api/v2/documents/{document_id}/simulate", json={})
    assert resp.status_code == 200
    import datetime

    assert resp.json()["reference_date"] == datetime.date.today().isoformat()


# ---- sensitivity tiering ----

PRIVILEGED_CONTRACT = (
    "PRIVILEGED AND CONFIDENTIAL. This memorandum is protected by the attorney-client "
    "privilege and was prepared in anticipation of litigation.\n\n"
    "The Tenant shall indemnify the Landlord for any damages."
)


@pytest.fixture
def privileged_document_id(client):
    resp = client.post("/api/upload",
                       files={"file": ("memo.txt", PRIVILEGED_CONTRACT.encode(), "text/plain")})
    return resp.json()["document_id"]


def test_upload_persists_the_sensitivity_tier(client):
    body = client.post("/api/upload",
                       files={"file": ("m.txt", PRIVILEGED_CONTRACT.encode(), "text/plain")}).json()
    assert body["sensitivity"]["tier"] == "privileged"
    assert body["sensitivity"]["external_providers_permitted"] is False
    doc = client.get(f"/api/v2/documents/{body['document_id']}").json()
    assert doc["sensitivity_tier"] == "privileged"
    assert doc["sensitivity_source"] == "auto"


def test_get_sensitivity_endpoint(client, privileged_document_id):
    body = client.get(f"/api/v2/documents/{privileged_document_id}/sensitivity").json()
    assert body["tier"] == "privileged"
    assert body["external_providers_permitted"] is False
    assert body["signals"]


def test_put_sensitivity_override_writes_an_audit_row(client, db_session, privileged_document_id):
    from app.db_models import AuditLog

    before = db_session.query(AuditLog).filter(AuditLog.detail.isnot(None)).count()
    resp = client.put(f"/api/v2/documents/{privileged_document_id}/sensitivity",
                      json={"tier": "internal", "reason": "reviewed and cleared by GC"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["tier"] == "internal"
    assert body["source"] == "override"
    # the suite runs with EXTERNAL_PROVIDERS_ENABLED=false, so 'internal' still
    # can't reach Class C -- but it's no longer *forbidden by tier*.
    from app.services.model_router import is_external_permitted
    assert body["external_providers_permitted"] == is_external_permitted("internal")

    rows = db_session.query(AuditLog).filter(AuditLog.detail.isnot(None)).all()
    assert len(rows) == before + 1
    assert "privileged -> internal" in rows[-1].detail
    assert "cleared by GC" in rows[-1].detail


def test_put_sensitivity_rejects_a_bad_tier(client, privileged_document_id):
    assert client.put(f"/api/v2/documents/{privileged_document_id}/sensitivity",
                      json={"tier": "top-secret", "reason": "x"}).status_code == 422
    assert client.put(f"/api/v2/documents/{privileged_document_id}/sensitivity",
                      json={"tier": "internal"}).status_code == 422  # reason required


def test_v2_analyze_surfaces_external_disabled_for_a_privileged_doc(client, privileged_document_id, monkeypatch):
    monkeypatch.setattr("app.services.contextualizer.rag.embed_content", fake_embed_content)
    resp = client.post(f"/api/v2/documents/{privileged_document_id}/analyze", json={"analysis_mode": "risk_only"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["sensitivity_tier"] == "privileged"
    assert body["external_providers_permitted"] is False
