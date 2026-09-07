"""
Tests for the node/edge-shaped graph export (LEARNING_LOG.md #53) using a
fake client (no real Memgraph needed) -- mirrors test_kg_builder.py's and
test_kg_versioning.py's pattern. A live Memgraph AND a real embedded Kuzu
database were both verified manually during development (see
LEARNING_LOG.md #53) -- test_kg_kuzu_client.py covers the real-Kuzu
round-trip.
"""
from app.services.kg import schema
from app.services.kg.builder import document_node_id
from app.services.kg.graph_export import get_document_graph


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


def test_noop_when_client_unavailable():
    fake = FakeKGClient(available=False)

    result = get_document_graph(fake, document_id=1)

    assert result == {"nodes": [], "edges": [], "kg_available": False}
    assert fake.queries == []


DOC_LOOKUP_MARKER = "RETURN d.id AS id, d.document_id"
CLAUSE_MARKER = "RETURN c.id AS id, c.content"
TERM_MARKER = "RETURN t.id AS id, t.term"
REF_MARKER = "RETURN DISTINCT c.id AS clause_id, r.id AS ref_id"
USES_TERM_MARKER = "RETURN DISTINCT c.id AS clause_id, t.id AS term_id"
SAME_AS_MARKER = "linked.term AS linked_term"


def test_empty_when_document_not_in_graph():
    # available=True, but the document-lookup query returns no rows (e.g.
    # never ingested) -- kg_available reflects that the graph itself is up,
    # just with nothing for this document.
    fake = FakeKGClient(canned={DOC_LOOKUP_MARKER: []})

    result = get_document_graph(fake, document_id=1)

    assert result == {"nodes": [], "edges": [], "kg_available": True}


def test_builds_nodes_and_edges_from_every_query():
    doc_id = document_node_id(5)
    fake = FakeKGClient(canned={
        DOC_LOOKUP_MARKER: [{"id": doc_id, "document_id": 5}],
        CLAUSE_MARKER: [{"id": "doc:5:clause:1", "text": "Some clause text.", "clause_type": "other"}],
        TERM_MARKER: [{"id": "doc:5:term:x", "term": "X"}],
    })

    result = get_document_graph(fake, document_id=5)

    node_ids = {n["id"] for n in result["nodes"]}
    assert doc_id in node_ids
    assert "doc:5:clause:1" in node_ids
    assert "doc:5:term:x" in node_ids
    assert {"source": "doc:5:clause:1", "target": doc_id, "type": schema.PART_OF} in result["edges"]
    assert {"source": doc_id, "target": "doc:5:term:x", "type": schema.DEFINES} in result["edges"]


def test_truncates_long_clause_text_for_the_label():
    doc_id = document_node_id(1)
    long_text = "A" * 200
    fake = FakeKGClient(canned={
        DOC_LOOKUP_MARKER: [{"id": doc_id, "document_id": 1}],
        CLAUSE_MARKER: [{"id": "doc:1:clause:1", "text": long_text, "clause_type": "other"}],
    })

    result = get_document_graph(fake, document_id=1)

    clause_node = next(n for n in result["nodes"] if n["id"] == "doc:1:clause:1")
    assert len(clause_node["label"]) <= 60
    assert clause_node["label"].endswith("…")


def test_portfolio_linked_term_is_flagged():
    doc_id = document_node_id(1)
    fake = FakeKGClient(canned={
        DOC_LOOKUP_MARKER: [{"id": doc_id, "document_id": 1}],
        SAME_AS_MARKER: [
            {"term_id": "doc:1:term:provider", "linked_id": "doc:2:term:provider", "linked_term": "Provider"},
        ],
    })

    result = get_document_graph(fake, document_id=1)

    linked_node = next(n for n in result["nodes"] if n["id"] == "doc:2:term:provider")
    assert linked_node["portfolio_linked"] is True
    assert {"source": "doc:1:term:provider", "target": "doc:2:term:provider", "type": schema.SAME_AS} \
        in result["edges"]


def test_ref_and_uses_term_edges_use_their_own_dedicated_queries():
    doc_id = document_node_id(1)
    fake = FakeKGClient(canned={
        DOC_LOOKUP_MARKER: [{"id": doc_id, "document_id": 1}],
        REF_MARKER: [{"clause_id": "doc:1:clause:1", "ref_id": "doc:1:ref:section 4.2", "text": "Section 4.2"}],
        USES_TERM_MARKER: [{"clause_id": "doc:1:clause:1", "term_id": "doc:1:term:provider"}],
    })

    result = get_document_graph(fake, document_id=1)

    assert {"source": "doc:1:clause:1", "target": "doc:1:ref:section 4.2", "type": schema.REFERENCES} \
        in result["edges"]
    assert {"source": "doc:1:clause:1", "target": "doc:1:term:provider", "type": schema.USES_TERM} \
        in result["edges"]
