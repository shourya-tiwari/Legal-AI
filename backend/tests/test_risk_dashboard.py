"""
Risk Dashboard aggregation (docs/v2/ROADMAP.md Phase 8, LEARNING_LOG.md #52):
per-category keyword-flag counts across a whole document, for a spider/
radar chart. Rule-based only, no model calls -- deterministic and fast.
"""
from app.services.nlp.pipeline import build_clause_objects
from app.services.risk_radar.detector import generate_risk_dashboard
from app.services.risk_radar.rules import RISK_CATEGORY_NAMES


def test_every_category_is_present_even_with_zero_flags():
    clauses = build_clause_objects("The parties will meet quarterly for a status update.")

    result = generate_risk_dashboard(clauses)

    assert set(result["categories"]) == set(RISK_CATEGORY_NAMES)
    assert all(count == 0 for count in result["categories"].values())
    assert result["total_flags"] == 0
    assert result["clause_findings"] == []


def test_aggregates_flags_across_multiple_clauses_and_categories():
    text = (
        "The Tenant shall indemnify the Landlord.\n\n"
        "Either party may terminate this Agreement upon 10 days notice.\n\n"
        "This non-compete restricts the Employee for two years."
    )
    clauses = build_clause_objects(text)

    result = generate_risk_dashboard(clauses)

    assert result["categories"]["Liability & Indemnification"] == 1
    assert result["categories"]["Termination & Renewal"] == 1
    assert result["categories"]["Restrictive Covenants"] == 1  # the non-compete regression, #52
    assert result["total_flags"] == 3
    assert len(result["clause_findings"]) == 3


def test_clause_findings_carry_the_originating_clause_id_for_drill_down():
    text = "The Tenant shall indemnify the Landlord for damages."
    clauses = build_clause_objects(text)

    result = generate_risk_dashboard(clauses)

    assert len(result["clause_findings"]) >= 1
    finding = result["clause_findings"][0]
    assert finding["clause_id"] == clauses[0].id
    assert finding["category"] == "Liability & Indemnification"
    assert finding["term"] == "indemnify"


def test_risk_dashboard_route_returns_stable_categories(client):
    upload_resp = client.post(
        "/api/upload",
        files={"file": ("q.txt", b"The Tenant shall indemnify the Landlord for damages.", "text/plain")},
    )
    document_id = upload_resp.json()["document_id"]

    resp = client.post(f"/api/v2/documents/{document_id}/risk-dashboard")

    assert resp.status_code == 200
    body = resp.json()
    assert set(body["categories"]) == set(RISK_CATEGORY_NAMES)
    # "indemnify" AND "damages" both appear in this sentence, both map to
    # the same category -- 2 flags, not 1 (a real, checked count, not assumed).
    assert body["categories"]["Liability & Indemnification"] == 2
    assert body["total_flags"] == 2


def test_risk_dashboard_route_unknown_document_returns_404(client):
    resp = client.post("/api/v2/documents/999999/risk-dashboard")
    assert resp.status_code == 404
