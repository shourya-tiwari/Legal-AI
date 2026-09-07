"""
Tests for bitemporal graph versioning (LEARNING_LOG.md #50) using a fake
client (no real Memgraph needed) -- mirrors test_kg_builder.py's pattern.
A live Memgraph AND a real embedded Kuzu database were both verified
manually against this exact module during development (see LEARNING_LOG.md
#50) -- this suite covers the query-construction/dispatch logic, not a
live-database integration test.
"""
from app.services.kg import schema
from app.services.kg.builder import document_node_id
from app.services.kg.versioning import (
    find_clauses_valid_as_of,
    find_document_version_history,
    mark_document_superseded,
)


class FakeKGClient:
    def __init__(self, available=True, canned=None):
        self._available = available
        self.queries = []
        self._canned = canned or {}

    @property
    def available(self):
        return self._available

    def run_query(self, cypher, **params):
        self.queries.append((cypher, params))
        for marker, rows in self._canned.items():
            if marker in cypher:
                return rows
        return []


def test_mark_document_superseded_noop_when_client_unavailable():
    fake = FakeKGClient(available=False)

    result = mark_document_superseded(fake, org_id=1, old_document_id=1, new_document_id=2)

    assert result == {"kg_available": False, "clauses_closed": 0}
    assert fake.queries == []


def test_mark_document_superseded_creates_edge_and_closes_old_clauses():
    fake = FakeKGClient(canned={"RETURN count(c) AS n": [{"n": 3}]})

    result = mark_document_superseded(
        fake, org_id=1, old_document_id=100, new_document_id=200, valid_from="2027-01-01T00:00:00+00:00",
    )

    assert result == {"kg_available": True, "valid_from": "2027-01-01T00:00:00+00:00", "clauses_closed": 3}
    cyphers = [q for q, _ in fake.queries]
    assert any(f"[r:{schema.SUPERSEDES}]" in c and "SET r.valid_from" in c for c in cyphers)
    assert any("SET c.valid_to = $effective" in c for c in cyphers)


def test_mark_document_superseded_defaults_valid_from_to_now_when_not_given():
    fake = FakeKGClient(canned={"RETURN count(c) AS n": [{"n": 1}]})

    result = mark_document_superseded(fake, org_id=1, old_document_id=1, new_document_id=2)

    assert result["valid_from"] is not None
    # A real ISO timestamp, not the placeholder -- confirms _now_iso-style
    # computation happened rather than leaving the field unset.
    assert "T" in result["valid_from"]


def test_find_document_version_history_noop_when_client_unavailable():
    fake = FakeKGClient(available=False)
    assert find_document_version_history(fake, document_id=1) == []


def test_find_document_version_history_queries_supersedes_chain():
    fake = FakeKGClient(canned={
        "UNWIND versions": [
            {"document_id": 100, "created_at": "t1", "valid_from": "t1"},
            {"document_id": 200, "created_at": "t2", "valid_from": "t2"},
        ]
    })

    history = find_document_version_history(fake, document_id=200)

    assert [h["document_id"] for h in history] == [100, 200]
    cypher = fake.queries[0][0]
    assert f"[:{schema.SUPERSEDES}*0..]" in cypher
    assert fake.queries[0][1]["doc_id"] == document_node_id(200)


def test_find_clauses_valid_as_of_noop_when_client_unavailable():
    fake = FakeKGClient(available=False)
    assert find_clauses_valid_as_of(fake, org_id=1, term="Tenant", as_of="2026-01-01") == []


def test_find_clauses_valid_as_of_filters_by_validity_window():
    fake = FakeKGClient(canned={
        "RETURN DISTINCT c.id": [
            {"clause_id": "c1", "text": "...", "clause_type": "other", "document_id": 1,
             "valid_from": "2026-01-01", "valid_to": None},
        ]
    })

    rows = find_clauses_valid_as_of(fake, org_id=1, term="Tenant", as_of="2026-06-01")

    assert len(rows) == 1
    cypher, params = fake.queries[0]
    assert "c.valid_from <= $as_of" in cypher
    assert "c.valid_to IS NULL OR c.valid_to > $as_of" in cypher
    assert params["as_of"] == "2026-06-01"
    assert params["term"] == "tenant"  # normalized, same as find_clauses_using_term
