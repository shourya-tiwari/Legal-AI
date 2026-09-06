"""
The embedded Kuzu KG backend (docs/v2/ROADMAP.md Phase 7 "Collapsed data
layer" -- the laptop/single-binary profile substitutes Memgraph for an
in-process, disk-backed graph database needing no server at all).

Unlike test_kg_builder.py (a FakeKGClient -- no real database involved at
all, since there's no way to stand up real Memgraph in this suite), these
tests run the exact same builder.py/queries.py functions against a real,
temporary, on-disk Kuzu database (`tmp_path` -- a fresh directory per test,
no leftover-state risk). This is the actual "verify the same application
code runs against either data-layer profile" proof for the graph half.
"""
from __future__ import annotations

import pytest

kuzu = pytest.importorskip("kuzu", reason="kuzu not installed -- the Kuzu KG backend is optional")

from app.services.kg.builder import link_portfolio_terms, write_document_graph
from app.services.kg.kuzu_client import KuzuKGClient
from app.services.kg.queries import find_clauses_using_term, find_potential_conflicts, get_document_graph_summary
from app.services.kg.schema import ensure_constraints
from app.services.nlp.pipeline import build_clause_objects

SAMPLE_TEXT = (
    'The Tenant ("Tenant") shall pay a security deposit within 30 days, as described in Section 4.2.'
)


@pytest.fixture
def kuzu_client(tmp_path):
    return KuzuKGClient(str(tmp_path / "kuzu_test_db"))


def test_kuzu_client_is_available_after_a_successful_open(kuzu_client):
    assert kuzu_client.available is True
    assert kuzu_client.backend == "kuzu"


def test_kuzu_client_reports_unavailable_and_fails_soft_on_open_error(monkeypatch, tmp_path):
    # kuzu is imported lazily inside __init__ (mirrors KGClient's own driver
    # import pattern) -- since imports are cached in sys.modules, patching
    # the already-imported real `kuzu` module's Database class is what the
    # module's own `import kuzu` will see.
    def _boom(*a, **k):
        raise RuntimeError("simulated: directory locked by another process")

    monkeypatch.setattr(kuzu, "Database", _boom)

    client = KuzuKGClient(str(tmp_path / "wont_open"))
    assert client.available is False
    assert client.run_query("MATCH (n) RETURN n") == []


def test_write_document_graph_then_find_clauses_using_term_round_trips_on_real_kuzu(kuzu_client):
    clauses = build_clause_objects(SAMPLE_TEXT)
    defined_terms = {"Tenant": "The Tenant (\"Tenant\")"}

    summary = write_document_graph(kuzu_client, org_id=1, document_id=1,
                                   defined_terms=defined_terms, clauses=clauses)
    assert summary["clauses"] == len(clauses)
    assert summary["defined_terms"] == 1

    found = find_clauses_using_term(kuzu_client, org_id=1, term="Tenant")
    assert len(found) >= 1
    assert all(row["document_id"] == 1 for row in found)
    assert any("security deposit" in row["text"] for row in found)


def test_get_document_graph_summary_on_real_kuzu(kuzu_client):
    clauses = build_clause_objects(SAMPLE_TEXT)
    write_document_graph(kuzu_client, org_id=1, document_id=7,
                         defined_terms={"Tenant": "ctx"}, clauses=clauses)

    summary = get_document_graph_summary(kuzu_client, document_id=7)
    assert summary["clause_count"] == len(clauses)
    assert "Tenant" in summary["defined_terms"]


def test_find_potential_conflicts_on_real_kuzu(kuzu_client):
    # Two documents, same defined term, opposite modalities -> a candidate conflict.
    obligation_text = 'The Vendor ("Vendor") shall deliver the goods within 10 days.'
    prohibition_text = 'The Vendor ("Vendor") shall not deliver the goods after termination.'

    write_document_graph(kuzu_client, org_id=1, document_id=1,
                         defined_terms={"Vendor": "ctx a"}, clauses=build_clause_objects(obligation_text))
    write_document_graph(kuzu_client, org_id=1, document_id=2,
                         defined_terms={"Vendor": "ctx b"}, clauses=build_clause_objects(prohibition_text))
    link_portfolio_terms(kuzu_client, org_id=1, document_id=2, defined_terms={"Vendor": "ctx b"})

    conflicts = find_potential_conflicts(kuzu_client, org_id=1, term="Vendor")
    assert len(conflicts) >= 1
    assert conflicts[0]["obligation"]["document_id"] != conflicts[0]["prohibition"]["document_id"]


def test_link_portfolio_terms_creates_a_same_as_edge_on_real_kuzu(kuzu_client):
    shared_context = 'Alpha Solutions Pvt. Ltd. ("Provider")'
    write_document_graph(kuzu_client, org_id=1, document_id=1,
                         defined_terms={"Provider": shared_context}, clauses=[])
    write_document_graph(kuzu_client, org_id=1, document_id=2,
                         defined_terms={"Provider": shared_context}, clauses=[])

    links = link_portfolio_terms(kuzu_client, org_id=1, document_id=2,
                                 defined_terms={"Provider": shared_context})
    assert links == 1


def test_ensure_constraints_noops_for_kuzu_backend(kuzu_client):
    # Must not raise -- Kuzu doesn't support Memgraph's CREATE CONSTRAINT
    # syntax at all, and doesn't need to (PRIMARY KEY already enforces it).
    ensure_constraints(kuzu_client)


def test_get_kg_client_dispatches_to_kuzu_when_configured(monkeypatch, tmp_path):
    from app.config import get_settings
    from app.services.kg.client import get_kg_client

    get_kg_client.cache_clear()
    monkeypatch.setenv("KG_BACKEND", "kuzu")
    monkeypatch.setenv("KUZU_DB_PATH", str(tmp_path / "dispatch_test_db"))
    get_settings.cache_clear()

    client = get_kg_client()
    assert client.backend == "kuzu"
    assert client.available is True

    get_kg_client.cache_clear()
    get_settings.cache_clear()
