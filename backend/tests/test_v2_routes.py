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
