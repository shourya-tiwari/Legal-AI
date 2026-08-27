"""
Tests for the KG builder/query logic using a fake client (no real Memgraph
needed) -- mirrors the fake-Redis pattern in test_rate_limit.py. A live
Memgraph is verified manually/in dev (docker-compose), not in this suite.
"""
from app.services.kg import schema
from app.services.kg.builder import (
    clause_node_id,
    cross_ref_node_id,
    document_node_id,
    link_portfolio_terms,
    normalize_term,
    should_link_terms,
    term_node_id,
    write_document_graph,
)
from app.services.nlp.pipeline import build_clause_objects


class FakeKGClient:
    def __init__(self, available=True, canned_others=None):
        self._available = available
        self.queries = []
        self._canned_others = canned_others or []

    @property
    def available(self):
        return self._available

    def run_query(self, cypher, **params):
        self.queries.append((cypher, params))
        if "otherDoc.id <> $doc_id" in cypher:
            return self._canned_others
        return []


SAMPLE_TEXT = (
    'The Tenant ("Tenant") shall pay a security deposit within 30 days, as described in Section 4.2.'
)


def test_node_id_helpers_are_stable_and_normalized():
    assert document_node_id(5) == "doc:5"
    assert clause_node_id(5, 1) == "doc:5:clause:1"
    assert term_node_id(5, "Tenant") == term_node_id(5, "  tenant  ")
    assert cross_ref_node_id(5, "Section 4.2") == "doc:5:ref:section 4.2"


def test_normalize_term_collapses_whitespace_and_case():
    assert normalize_term("  The   Company ") == "the company"


def test_write_document_graph_noop_when_client_unavailable():
    fake = FakeKGClient(available=False)
    clauses = build_clause_objects(SAMPLE_TEXT)

    summary = write_document_graph(fake, org_id=1, document_id=1, defined_terms={"Tenant": "ctx"}, clauses=clauses)

    assert summary == {"clauses": 0, "defined_terms": 0, "cross_references": 0}
    assert fake.queries == []


def test_write_document_graph_issues_expected_node_and_edge_writes():
    fake = FakeKGClient()
    clauses = build_clause_objects(SAMPLE_TEXT)
    defined_terms = {"Tenant": "context"}

    summary = write_document_graph(fake, org_id=1, document_id=42, defined_terms=defined_terms, clauses=clauses)

    assert summary["clauses"] == len(clauses)
    assert summary["defined_terms"] == 1
    assert summary["cross_references"] == 1  # "Section 4.2"

    cyphers = [q for q, _ in fake.queries]
    assert any(f"MERGE (d:{schema.DOCUMENT}" in c for c in cyphers)
    assert any(f"MERGE (t:{schema.DEFINED_TERM}" in c for c in cyphers)
    assert any(f"MERGE (c:{schema.CLAUSE}" in c for c in cyphers)
    assert any(f"[:{schema.PART_OF}]" in c for c in cyphers)
    assert any(f"[:{schema.USES_TERM}]" in c for c in cyphers)
    assert any(f"[:{schema.REFERENCES}]" in c for c in cyphers)
    assert any(f"[:{schema.DEFINES}]" in c for c in cyphers)


def test_should_link_terms_requires_matching_alias_and_similar_context():
    assert should_link_terms(
        "Provider", 'Alpha Solutions Pvt. Ltd. ("Provider")',
        "Provider", 'Alpha Solutions Pvt. Ltd. ("Provider")',
    ) is True
    assert should_link_terms(
        "Provider", 'Alpha Solutions Pvt. Ltd. ("Provider")',
        "Vendor", 'Alpha Solutions Pvt. Ltd. ("Vendor")',
    ) is False  # different alias text
    assert should_link_terms(
        "Company", 'Alpha Solutions Pvt. Ltd. ("Company")',
        "Company", 'Zeta Consulting LLC ("Company")',
    ) is False  # same alias, unrelated underlying entity


def test_link_portfolio_terms_creates_same_as_edge_for_a_plausible_match():
    fake = FakeKGClient(canned_others=[
        {"id": "doc:1:term:provider", "term": "Provider", "context": 'Alpha Solutions Pvt. Ltd. ("Provider")'},
    ])
    defined_terms = {"Provider": 'Alpha Solutions Pvt. Ltd. ("Provider")'}

    links = link_portfolio_terms(fake, org_id=1, document_id=2, defined_terms=defined_terms)

    assert links == 1
    same_as_queries = [q for q, _ in fake.queries if f"[:{schema.SAME_AS}]" in q]
    assert len(same_as_queries) == 1


def test_link_portfolio_terms_creates_no_edge_when_no_match():
    fake = FakeKGClient(canned_others=[
        {"id": "doc:1:term:company", "term": "Company", "context": 'Zeta Consulting LLC ("Company")'},
    ])
    defined_terms = {"Provider": 'Alpha Solutions Pvt. Ltd. ("Provider")'}

    links = link_portfolio_terms(fake, org_id=1, document_id=2, defined_terms=defined_terms)

    assert links == 0
