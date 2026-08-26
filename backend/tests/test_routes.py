"""
Route-level tests for all 6 /api endpoints, with every Gemini call mocked
so these tests never hit the network or require a real GOOGLE_API_KEY.
"""
from types import SimpleNamespace

import pytest


def fake_generate_content(prompt, **kwargs):
    if "hierarchical structure" in prompt:
        return '[{"title": "Section 1", "content_summary": "Intro clause", "subsections": []}]'
    if "time-based obligations" in prompt:
        return '[{"date_description": "January 1, 2025", "event": "Agreement begins"}]'
    if "high-risk terms" in prompt:
        return '{"flags": [{"term": "penalty fee", "explanation": "May indicate financial risk"}]}'
    if "helpful legal assistant" in prompt:
        return "The contract can be terminated with 30 days notice."
    if "advising a" in prompt:
        return "For you, this means you should review the notice period carefully."
    return "This means the tenant must pay rent every month."


def fake_embed_content(contents, model=None):
    vecs = [SimpleNamespace(values=[0.1, 0.2, 0.3, 0.4]) for _ in contents]
    return SimpleNamespace(embeddings=vecs)


def test_health_endpoint(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "running" in resp.json()["message"]


def test_upload_txt_file(client):
    files = {"file": ("contract.txt", b"This Agreement is made on January 1, 2025.", "text/plain")}
    resp = client.post("/api/upload", files=files)

    assert resp.status_code == 200
    body = resp.json()
    assert body["filename"] == "contract.txt"
    assert "January 1, 2025" in body["full_text"]
    assert body["count"] == len(body["clauses"])


def test_upload_missing_file_returns_400(client):
    resp = client.post("/api/upload")
    assert resp.status_code in (400, 422)


def test_rewrite_endpoint(client, monkeypatch):
    monkeypatch.setattr("app.services.rewriter.generate_content", fake_generate_content)

    resp = client.post("/api/rewrite", json={"text": "The Tenant shall pay rent monthly.", "mode": "layman"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["rewritten_text"]
    assert body["meta"]["chunks"] == 1


def test_rewrite_rejects_unsupported_mode(client):
    resp = client.post("/api/rewrite", json={"text": "Some clause.", "mode": "advanced"})
    assert resp.status_code == 422


def test_map_endpoint(client, monkeypatch):
    monkeypatch.setattr("app.services.timeline.generate_content", fake_generate_content)

    resp = client.post("/api/map", json={"contract_text": "This Agreement begins January 1, 2025."})

    assert resp.status_code == 200
    body = resp.json()
    assert body["structure"][0]["title"] == "Section 1"
    assert body["timeline"][0]["event"] == "Agreement begins"


def test_ask_endpoint(client, monkeypatch):
    monkeypatch.setattr("app.services.chatbot.generate_content", fake_generate_content)

    resp = client.post(
        "/api/ask",
        json={"contract_text": "Either party may terminate with 30 days notice.", "question": "How do I terminate?"},
    )

    assert resp.status_code == 200
    assert "30 days" in resp.json()["answer"]


def test_risk_scan_endpoint(client, monkeypatch):
    monkeypatch.setattr("app.services.risk_radar.detector.generate_content", fake_generate_content)

    resp = client.post("/api/risk/scan", json={"text": "The Tenant shall indemnify the Landlord."})

    assert resp.status_code == 200
    body = resp.json()
    flagged = body["flagged_clauses"][0]
    keyword_terms = {f["term"] for f in flagged["keyword_flags"]}
    assert "indemnify" in keyword_terms
    contextual_terms = {f["term"] for f in flagged["contextual_flags"]}
    assert "penalty fee" in contextual_terms


def test_contextualize_endpoint(client, monkeypatch):
    monkeypatch.setattr("app.services.contextualizer.explainer.generate_content", fake_generate_content)
    monkeypatch.setattr("app.services.contextualizer.rag.embed_content", fake_embed_content)
    # Reset the module-level RAG index singleton so this test controls its build.
    import app.services.contextualizer.explainer as explainer_module
    explainer_module._rag_index = None

    resp = client.post(
        "/api/contextualize/scan",
        json={
            "text": "Tenant shall pay a security deposit equal to two months' rent.",
            "context": {"role": "tenant", "location": "California", "contract_type": "lease", "tone": "plain"},
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert "For you, this means" in body["explanation"]
