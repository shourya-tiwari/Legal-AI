"""
Episodic-tier memory (app/services/memory/episodic.py, docs/v2/AGENTS.md's
Memory system, Phase 7) -- reads the CaseAnalysis table that already
exists, and finds similar past analyses via the same embed-then-cosine-
similarity approach app/services/consistency.py established.

Uses a freshly-created Organization per test rather than the shared
default org: find_similar_past_analyses deliberately scans up to the last
50 of an org's CaseAnalysis rows, so reusing one shared org across tests
(LEARNING_LOG.md #30's standing hazard) would let an earlier test's rows
leak into a later test's similarity search and its exact-match assertions.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.db_models import CaseAnalysis, Document, Organization
from app.services.memory.episodic import find_similar_past_analyses, get_document_episodic_history


def _fake_embed_content(contents, model=None, task=None):
    # Deterministic, hand-crafted vectors: the "similar" candidate is
    # identical to the query and the "dissimilar" one is orthogonal to it --
    # lets the test assert on which candidate matches without depending on
    # a real embedding model's actual output.
    vecs = {
        "the tenant must indemnify the landlord for damages": [1.0, 0.0, 0.0],
        "the vendor must indemnify the client for losses": [1.0, 0.0, 0.0],
        "bananas grow on trees in tropical climates": [0.0, 1.0, 0.0],
    }
    return SimpleNamespace(embeddings=[
        SimpleNamespace(values=vecs.get(c.lower(), [0.5, 0.5, 0.5])) for c in contents
    ])


@pytest.fixture
def org(db_session, request):
    o = Organization(name=f"episodic-test-org-{request.node.name}")
    db_session.add(o)
    db_session.commit()
    db_session.refresh(o)
    return o


def _make_document(db_session, org_id: int) -> int:
    doc = Document(org_id=org_id, filename="q.txt", full_text="Some contract text.")
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    return doc.id


def _add_analysis(db_session, org_id: int, document_id: int, summary: str) -> CaseAnalysis:
    row = CaseAnalysis(org_id=org_id, document_id=document_id, analysis_mode="full",
                       summary=summary, faithfulness_ok=True, faithfulness_method="nli")
    db_session.add(row)
    db_session.commit()
    return row


def test_get_document_episodic_history_returns_most_recent_first(db_session, org):
    doc_id = _make_document(db_session, org.id)
    _add_analysis(db_session, org.id, doc_id, "First pass.")
    _add_analysis(db_session, org.id, doc_id, "Second pass, more thorough.")

    history = get_document_episodic_history(db_session, org.id, doc_id)
    assert [h.summary for h in history] == ["Second pass, more thorough.", "First pass."]


def test_get_document_episodic_history_is_scoped_to_the_document(db_session, org):
    doc_a = _make_document(db_session, org.id)
    doc_b = _make_document(db_session, org.id)
    _add_analysis(db_session, org.id, doc_a, "For doc A.")
    _add_analysis(db_session, org.id, doc_b, "For doc B.")

    history = get_document_episodic_history(db_session, org.id, doc_a)
    assert [h.summary for h in history] == ["For doc A."]


def test_find_similar_past_analyses_finds_the_similar_one_and_excludes_the_dissimilar_one(db_session, org, monkeypatch):
    monkeypatch.setattr("app.services.memory.episodic.embed_content", _fake_embed_content)

    doc_a = _make_document(db_session, org.id)
    doc_b = _make_document(db_session, org.id)
    _add_analysis(db_session, org.id, doc_a, "The vendor must indemnify the client for losses")
    _add_analysis(db_session, org.id, doc_b, "Bananas grow on trees in tropical climates")

    matches = find_similar_past_analyses(
        db_session, org.id, "The tenant must indemnify the landlord for damages",
    )

    assert len(matches) == 1
    assert matches[0]["document_id"] == doc_a
    assert matches[0]["similarity"] > 0.9


def test_find_similar_past_analyses_excludes_the_named_document(db_session, org, monkeypatch):
    monkeypatch.setattr("app.services.memory.episodic.embed_content", _fake_embed_content)

    doc_a = _make_document(db_session, org.id)
    _add_analysis(db_session, org.id, doc_a, "The vendor must indemnify the client for losses")

    matches = find_similar_past_analyses(
        db_session, org.id, "The tenant must indemnify the landlord for damages",
        exclude_document_id=doc_a,
    )
    assert matches == []


def test_find_similar_past_analyses_returns_empty_for_blank_query(db_session, org):
    assert find_similar_past_analyses(db_session, org.id, "   ") == []
