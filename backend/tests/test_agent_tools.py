"""
Typed tool interfaces (app/agents/tools.py, docs/v2/AGENTS.md "Tool
interface", Phase 7). Every tool here wraps an already-tested service
function -- these tests focus on the *typed-interface* contract itself
(validation, dispatch, schema shape), not re-testing the wrapped service's
own logic (find_clauses_using_term etc. are already covered in
test_kg_builder.py / test_kg_kuzu_client.py).
"""
from __future__ import annotations

import datetime

import pytest
from pydantic import BaseModel

from app.agents.tools import (
    TOOL_REGISTRY,
    ClauseDiffOutput,
    DateMathOutput,
    ToolError,
    call_tool,
    tool_json_schemas,
)


# --------------------------------------------------------------------------
# call_tool dispatch + validation
# --------------------------------------------------------------------------

def test_call_tool_rejects_an_unknown_tool_name():
    with pytest.raises(ToolError, match="Unknown tool"):
        call_tool("not_a_real_tool")


def test_call_tool_rejects_invalid_input():
    with pytest.raises(ToolError, match="Invalid input"):
        call_tool("kg_query", org_id="not-an-int", term="")  # empty term violates min_length


def test_call_tool_rejects_a_tool_that_returns_the_wrong_output_type(monkeypatch):
    from app.agents import tools as tools_module

    bad_spec = tools_module.ToolSpec(
        "broken", "returns the wrong type", tools_module.KGQueryInput, tools_module.KGQueryOutput,
        lambda input: "not a KGQueryOutput",
    )
    monkeypatch.setitem(TOOL_REGISTRY, "broken", bad_spec)
    with pytest.raises(ToolError, match="expected KGQueryOutput"):
        call_tool("broken", org_id=1, term="tenant")


def test_every_registered_tool_has_a_json_schema():
    schemas = tool_json_schemas()
    assert set(schemas) == set(TOOL_REGISTRY)
    for name, schema in schemas.items():
        assert "properties" in schema, name


# --------------------------------------------------------------------------
# date_math -- deterministic, no mocking needed
# --------------------------------------------------------------------------

def test_date_math_adds_days():
    result = call_tool("date_math", reference_date="2026-01-01", amount=30, unit="day", direction="after")
    assert isinstance(result, DateMathOutput)
    assert result.result_date == datetime.date(2026, 1, 31)


def test_date_math_subtracts_days():
    result = call_tool("date_math", reference_date="2026-01-31", amount=30, unit="day", direction="before")
    assert result.result_date == datetime.date(2026, 1, 1)


def test_date_math_handles_month_arithmetic_across_a_shorter_month():
    # Jan 31 + 1 month must not silently overflow into March -- relativedelta
    # clamps to the shorter month's last valid day.
    result = call_tool("date_math", reference_date="2026-01-31", amount=1, unit="month", direction="after")
    assert result.result_date == datetime.date(2026, 2, 28)  # 2026 is not a leap year


def test_date_math_rejects_an_invalid_unit():
    with pytest.raises(ToolError, match="unit must be one of"):
        call_tool("date_math", reference_date="2026-01-01", amount=1, unit="fortnight", direction="after")


def test_date_math_rejects_an_invalid_direction():
    with pytest.raises(ToolError, match="direction must be"):
        call_tool("date_math", reference_date="2026-01-01", amount=1, unit="day", direction="sideways")


# --------------------------------------------------------------------------
# clause_diff -- deterministic, stdlib difflib
# --------------------------------------------------------------------------

def test_clause_diff_identical_clauses_have_similarity_one_and_no_diff():
    result = call_tool("clause_diff", clause_a="The Tenant shall pay rent.", clause_b="The Tenant shall pay rent.")
    assert isinstance(result, ClauseDiffOutput)
    assert result.similarity == 1.0
    assert result.diff_lines == []


def test_clause_diff_different_clauses_have_lower_similarity_and_a_diff():
    result = call_tool("clause_diff", clause_a="The Tenant shall pay rent monthly.",
                       clause_b="The Tenant shall pay rent annually in advance.")
    assert 0.0 < result.similarity < 1.0
    assert result.diff_lines  # a non-empty unified diff


# --------------------------------------------------------------------------
# kg_query / kg_conflicts -- Memgraph is unreachable in the test environment
# (see conftest.py), so these exercise the fail-soft empty-result path.
# --------------------------------------------------------------------------

def test_kg_query_fails_soft_to_an_empty_result_without_a_reachable_graph():
    result = call_tool("kg_query", org_id=1, term="tenant")
    assert result.matches == []


def test_kg_conflicts_fails_soft_to_an_empty_result_without_a_reachable_graph():
    result = call_tool("kg_conflicts", org_id=1, term="tenant")
    assert result.conflicts == []


# --------------------------------------------------------------------------
# vector_search -- mocked hybrid_search, matching test_routes.py's convention
# --------------------------------------------------------------------------

def test_vector_search_wraps_hybrid_search(monkeypatch):
    from app.services.rag.corpus import LegalKnowledgeEntry

    fake_entries = [LegalKnowledgeEntry(text="Security deposits must be returned within 21 days.",
                                        topic="lease", citation="Cal. Civ. Code § 1950.5")]
    # hybrid_search is imported lazily inside _vector_search, so the patch
    # target is the real module it's imported from, not app.agents.tools.
    monkeypatch.setattr("app.services.rag.hybrid.hybrid_search", lambda query, k=3: fake_entries)

    result = call_tool("vector_search", query="security deposit return", k=3)
    assert len(result.hits) == 1
    assert result.hits[0].citation == "Cal. Civ. Code § 1950.5"


# --------------------------------------------------------------------------
# statute_lookup -- the real corpus, no mocking
# --------------------------------------------------------------------------

def test_statute_lookup_returns_only_entries_with_a_real_citation():
    result = call_tool("statute_lookup", topic="lease")
    assert result.citations  # the corpus has real lease citations
    assert all(c.citation is not None for c in result.citations)
    assert any("1950.5" in c.citation for c in result.citations)


def test_statute_lookup_returns_empty_for_an_unknown_topic():
    result = call_tool("statute_lookup", topic="maritime_law")
    assert result.citations == []


# --------------------------------------------------------------------------
# request_human_approval -- honestly non-blocking
# --------------------------------------------------------------------------

def test_request_human_approval_returns_a_pending_marker_without_blocking():
    result = call_tool("request_human_approval", payload={"clause_id": 5}, reason="Ambiguous indemnity scope.")
    assert result.status == "pending_review"
    assert result.reason == "Ambiguous indemnity scope."
