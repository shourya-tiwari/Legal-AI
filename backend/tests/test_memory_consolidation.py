"""
Memory consolidation worker (app/services/memory/consolidation.py,
docs/v2/AGENTS.md's Memory system, Phase 7) -- promotes recurring risk
terms across an org's non-privileged documents into semantic memory, with
an unconditional privacy-tier gate (a privileged document's data never
counts, no opt-in override exists).

Uses a freshly-created Organization per test rather than the shared
default org `client`'s no-auth uploads land in -- consolidate_org_memory
deliberately re-scans *all* of an org's CaseAnalysis history on every call,
so reusing the one shared default org across tests (LEARNING_LOG.md #30's
standing hazard) would let one test's promoted entries leak into another
test's `entries == []` assertions.
"""
from __future__ import annotations

import pytest

from app.db_models import CaseAnalysis, Document, Organization, SemanticMemoryEntry
from app.services.memory.consolidation import consolidate_org_memory


@pytest.fixture
def org(db_session, request):
    o = Organization(name=f"consolidation-test-org-{request.node.name}")
    db_session.add(o)
    db_session.commit()
    db_session.refresh(o)
    return o


def _make_document(db_session, org_id: int, tier: str = "internal") -> int:
    doc = Document(org_id=org_id, filename="q.txt", full_text="Some contract text.", sensitivity_tier=tier)
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    return doc.id


def _analysis_with_finding(org_id: int, document_id: int, term: str) -> CaseAnalysis:
    return CaseAnalysis(
        org_id=org_id, document_id=document_id, analysis_mode="full",
        summary="x", faithfulness_ok=True, faithfulness_method="nli",
        risk_findings=[{"clause_id": 1, "term": term, "explanation": "e", "source": "keyword"}],
    )


def test_a_term_recurring_across_two_documents_is_promoted(db_session, org):
    doc_a = _make_document(db_session, org.id)
    doc_b = _make_document(db_session, org.id)

    db_session.add(_analysis_with_finding(org.id, doc_a, "indemnify"))
    db_session.add(_analysis_with_finding(org.id, doc_b, "indemnify"))
    db_session.commit()

    entries = consolidate_org_memory(db_session, org.id)

    assert len(entries) == 1
    assert entries[0].pattern_key == "indemnify"
    assert entries[0].occurrence_count == 2
    assert sorted(entries[0].supporting_document_ids) == sorted([doc_a, doc_b])


def test_a_term_seen_on_only_one_document_is_not_promoted(db_session, org):
    doc_a = _make_document(db_session, org.id)
    db_session.add(_analysis_with_finding(org.id, doc_a, "liquidated damages"))
    db_session.commit()

    entries = consolidate_org_memory(db_session, org.id)
    assert entries == []


def test_privileged_documents_are_never_promoted_even_with_a_recurring_term(db_session, org):
    doc_a = _make_document(db_session, org.id, tier="privileged")
    doc_b = _make_document(db_session, org.id, tier="privileged")

    db_session.add(_analysis_with_finding(org.id, doc_a, "non-compete"))
    db_session.add(_analysis_with_finding(org.id, doc_b, "non-compete"))
    db_session.commit()

    entries = consolidate_org_memory(db_session, org.id)
    assert entries == []
    assert db_session.query(SemanticMemoryEntry).filter_by(org_id=org.id, pattern_key="non-compete").first() is None


def test_a_privileged_document_does_not_count_toward_the_occurrence_threshold(db_session, org):
    # Non-privileged + privileged sharing a term must NOT reach the
    # 2-occurrence threshold via the privileged one -- only 1 legitimate
    # (non-privileged) occurrence exists.
    doc_a = _make_document(db_session, org.id, tier="internal")
    doc_b = _make_document(db_session, org.id, tier="privileged")

    db_session.add(_analysis_with_finding(org.id, doc_a, "arbitration"))
    db_session.add(_analysis_with_finding(org.id, doc_b, "arbitration"))
    db_session.commit()

    entries = consolidate_org_memory(db_session, org.id)
    assert entries == []


def test_consolidation_is_idempotent_and_updates_an_existing_entry(db_session, org):
    doc_a = _make_document(db_session, org.id)
    doc_b = _make_document(db_session, org.id)
    db_session.add(_analysis_with_finding(org.id, doc_a, "confidentiality"))
    db_session.add(_analysis_with_finding(org.id, doc_b, "confidentiality"))
    db_session.commit()

    first_run = consolidate_org_memory(db_session, org.id)
    assert len(first_run) == 1
    entry_id = first_run[0].id

    doc_c = _make_document(db_session, org.id)
    db_session.add(_analysis_with_finding(org.id, doc_c, "confidentiality"))
    db_session.commit()

    second_run = consolidate_org_memory(db_session, org.id)
    assert len(second_run) == 1
    assert second_run[0].id == entry_id  # updated in place, not duplicated
    assert second_run[0].occurrence_count == 3

    assert db_session.query(SemanticMemoryEntry).filter_by(org_id=org.id, pattern_key="confidentiality").count() == 1
