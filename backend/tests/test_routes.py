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


def fake_embed_content(contents, model=None, task=None):
    # Matches the real embed_content(contents, *, model=None, task=...)
    # signature -- callers that wrap this in a try/except (e.g.
    # contextualizer/rag.py's fail-soft embed_texts) previously masked a
    # missing `task` kwarg here as a silently-swallowed TypeError. A caller
    # that calls embed_content unguarded (app/services/consistency.py) surfaces
    # a signature mismatch as a real test failure instead, which is what
    # caught this.
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
    body = resp.json()
    assert "30 days" in body["answer"]
    # Additive faithfulness fields (app/services/faithfulness.py) -- the
    # fake answer restates the exact wording of the contract text, so even
    # the weaker lexical-overlap fallback (NLI_ENABLED=false in tests)
    # should call it faithful.
    assert body["faithfulness_method"] == "lexical_fallback"
    assert body["faithful"] is True
    assert body["unsupported_claims"] == []


def test_ask_endpoint_flags_an_answer_unrelated_to_the_contract(client, monkeypatch):
    # Must be >= 25 chars (app/services/faithfulness.py's _MIN_CLAIM_CHARS) --
    # a shorter "claim" is skipped as a trivial fragment before any check
    # runs at all, which would vacuously pass instead of testing the flag.
    monkeypatch.setattr(
        "app.services.chatbot.generate_content",
        lambda *a, **k: "Bananas grow on trees in tropical climates around the world.",
    )

    resp = client.post(
        "/api/ask",
        json={"contract_text": "Either party may terminate with 30 days notice.", "question": "How do I terminate?"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["faithful"] is False
    assert body["faithfulness_method"] == "lexical_fallback"


def test_v1_routes_classify_sensitivity_on_the_fly(client, monkeypatch):
    """A V1 request has no persisted document -- the route classifies the
    provided text and threads the tier into the service's generate call."""
    captured = {}

    def spy(prompt, **kwargs):
        captured["sensitivity"] = kwargs.get("sensitivity")
        return "The contract can be terminated with 30 days notice."

    monkeypatch.setattr("app.services.chatbot.generate_content", spy)
    resp = client.post("/api/ask", json={
        "contract_text": "This memo is protected by the attorney-client privilege.",
        "question": "What does this mean?",
    })
    assert resp.status_code == 200
    assert captured["sensitivity"] == "privileged"


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
    # Reset the module-level dense-index singleton so this test controls its build.
    import app.services.rag.hybrid as hybrid_module
    hybrid_module._dense_index = None

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


def test_nlp_analyze_endpoint(client):
    resp = client.post(
        "/api/nlp/analyze",
        json={"contract_text": 'The Tenant ("Tenant") shall pay a security deposit within 30 days.'},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["clauses"]) == 1
    clause = body["clauses"][0]
    assert clause["clause_type_source"] == "rule"
    assert "Tenant" in clause["defined_terms_used"]
    assert any(t["modality"] == "obligation" for t in clause["deontic_tags"])


def test_kg_ingest_endpoint_fails_soft_without_memgraph_running(client):
    files = {"file": ("lease.txt", b'The Tenant ("Tenant") shall pay rent within 30 days.', "text/plain")}
    upload_resp = client.post("/api/upload", files=files)
    document_id = upload_resp.json()["document_id"]

    resp = client.post("/api/kg/ingest", json={"document_id": document_id})

    assert resp.status_code == 200
    body = resp.json()
    assert body["document_id"] == document_id
    # No Memgraph running in the test environment -- ingest still succeeds,
    # it just reports that nothing was actually written (fail-soft).
    assert body["kg_available"] is False
    assert body["clauses"] == 0


def test_kg_ingest_unknown_document_returns_404(client):
    resp = client.post("/api/kg/ingest", json={"document_id": 999999})
    assert resp.status_code == 404


def test_kg_query_endpoint_returns_empty_without_memgraph_running(client):
    resp = client.post("/api/kg/query", json={"term": "Tenant"})
    assert resp.status_code == 200
    assert resp.json()["clauses"] == []


def test_agents_analyze_endpoint(client, monkeypatch):
    monkeypatch.setattr("app.services.contextualizer.rag.embed_content", fake_embed_content)
    monkeypatch.setattr("app.agents.summary.generate_content", lambda *a, **k: "Risk summary, no citations.")
    # Reset the shared dense-index singleton -- an earlier test may have built
    # it with a differently-shaped (but also fake) embedding vector, and FAISS
    # asserts on a dimension mismatch rather than just failing the search.
    import app.services.rag.hybrid as hybrid_module
    hybrid_module._dense_index = None

    files = {
        "file": (
            "lease.txt",
            b'The Tenant ("Tenant") shall indemnify the Landlord for damages.\n\n'
            b"The Tenant shall not sublease the premises without written consent.",
            "text/plain",
        )
    }
    document_id = client.post("/api/upload", files=files).json()["document_id"]

    resp = client.post("/api/agents/analyze", json={"document_id": document_id})

    assert resp.status_code == 200
    body = resp.json()
    assert body["clause_count"] == 2
    assert any(f["term"] == "indemnify" for f in body["risk_findings"])
    assert body["summary"] == "Risk summary, no citations."
    # "indemnify" + "shall not" -> the planner picks the full plan
    assert [step["agent_name"] for step in body["trace"]] == [
        "extraction", "planner", "risk_compliance", "clause_research", "summary", "verifier",
    ]
    assert body["plan"] == ["risk_compliance", "research", "summarize", "verifier"]


def test_agents_analyze_unknown_document_returns_404(client):
    resp = client.post("/api/agents/analyze", json={"document_id": 999999})
    assert resp.status_code == 404


def test_agents_analyze_dispatches_to_the_durable_engine_when_enabled(client, monkeypatch):
    # A real dbos+Postgres round trip is tests/test_dbos_engine.py's job
    # (needs DBOS_TEST_DATABASE_URL). This confirms only the *dispatch*
    # logic in routes/agents.py::run_and_persist_analysis -- injecting a
    # fake module into sys.modules so the lazy `from
    # app.services.durable.dbos_engine import run_case_analysis_durable`
    # picks up the fake instead of importing the real module (which would
    # otherwise require `dbos` installed and a live Postgres connection
    # just to import, since DBOS(config=...) runs at that module's import
    # time) -- see dbos_engine.py's own docstring on why.
    import sys
    import types

    from app.agents.state import CaseState
    from app.config import get_settings

    called = {}

    def fake_run_case_analysis_durable(document_id, org_id, full_text, **kwargs):
        called["args"] = (document_id, org_id, full_text, kwargs)
        return CaseState(document_id=document_id, org_id=org_id, full_text=full_text,
                         plan=["verifier"], ran_steps=["extraction", "planner", "verifier"])

    fake_module = types.SimpleNamespace(run_case_analysis_durable=fake_run_case_analysis_durable)
    monkeypatch.setitem(sys.modules, "app.services.durable.dbos_engine", fake_module)
    monkeypatch.setattr(get_settings(), "DURABLE_EXECUTION_ENABLED", True)

    files = {"file": ("q.txt", b"Some contract text.", "text/plain")}
    document_id = client.post("/api/upload", files=files).json()["document_id"]

    resp = client.post("/api/agents/analyze", json={"document_id": document_id})

    assert resp.status_code == 200
    assert called["args"][0] == document_id
    assert resp.json()["plan"] == ["verifier"]
