"""
The human-in-the-loop review queue (docs/v2/ROADMAP.md Phase 7):
CaseAnalysis persists needs_human_review so it can actually be listed and
resolved, instead of only appearing in the one-shot analyze() response.
Inserts CaseAnalysis rows directly (db_session) rather than driving a real
agent run through mocks -- isolates the queue's own list/resolve logic from
the agent pipeline, which is already covered elsewhere (test_agents.py).
"""
from app.db_models import CaseAnalysis, Document


def _upload(client) -> int:
    resp = client.post("/api/upload", files={"file": ("q.txt", b"Some contract text.", "text/plain")})
    assert resp.status_code == 200
    return resp.json()["document_id"]


def test_review_queue_lists_only_unresolved_by_default(client, db_session):
    doc_id = _upload(client)
    flagged = CaseAnalysis(
        org_id=1, document_id=doc_id, analysis_mode="full", plan=["verifier"],
        summary="Flagged summary.", faithfulness_ok=False, faithfulness_method="nli",
        unsupported_claims=["claim one"], invalid_citation_numbers=[9],
        needs_human_review=True,
    )
    resolved = CaseAnalysis(
        org_id=1, document_id=doc_id, analysis_mode="full", plan=["verifier"],
        summary="Already handled.", faithfulness_ok=True, faithfulness_method="nli",
        needs_human_review=True, reviewed=True,
    )
    clean = CaseAnalysis(
        org_id=1, document_id=doc_id, analysis_mode="full", plan=["verifier"],
        summary="Nothing to see here.", faithfulness_ok=True, faithfulness_method="nli",
        needs_human_review=False,
    )
    db_session.add_all([flagged, resolved, clean])
    db_session.commit()

    resp = client.get("/api/review-queue")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["summary"] == "Flagged summary."
    assert items[0]["document_filename"] == "q.txt"
    assert items[0]["unsupported_claims"] == ["claim one"]
    assert items[0]["invalid_citation_numbers"] == [9]
    assert items[0]["reviewed"] is False


def test_review_queue_include_resolved(client, db_session):
    doc_id = _upload(client)
    db_session.add(CaseAnalysis(
        org_id=1, document_id=doc_id, analysis_mode="full", summary="Handled already.",
        faithfulness_ok=True, faithfulness_method="nli", needs_human_review=True, reviewed=True,
    ))
    db_session.commit()

    default_resp = client.get("/api/review-queue")
    assert all(not i["reviewed"] for i in default_resp.json()["items"])

    with_resolved = client.get("/api/review-queue", params={"include_resolved": True})
    assert any(i["summary"] == "Handled already." for i in with_resolved.json()["items"])


def test_resolve_review_item_marks_it_reviewed(client, db_session):
    doc_id = _upload(client)
    analysis = CaseAnalysis(
        org_id=1, document_id=doc_id, analysis_mode="full", summary="Needs a look.",
        faithfulness_ok=False, faithfulness_method="lexical_fallback", needs_human_review=True,
    )
    db_session.add(analysis)
    db_session.commit()
    db_session.refresh(analysis)

    resp = client.post(f"/api/review-queue/{analysis.id}/resolve", json={"note": "Checked, looks fine."})
    assert resp.status_code == 200
    body = resp.json()
    assert body["reviewed"] is True
    assert body["reviewer_note"] == "Checked, looks fine."
    assert body["reviewed_at"] is not None

    # no longer in the default (unresolved-only) queue
    queue = client.get("/api/review-queue").json()["items"]
    assert all(i["id"] != analysis.id for i in queue)


def test_resolve_unknown_analysis_is_404(client):
    resp = client.post("/api/review-queue/999999/resolve", json={})
    assert resp.status_code == 404
