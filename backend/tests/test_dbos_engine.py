"""
Durable execution via DBOS (docs/v2/ROADMAP.md Phase 7 "Durable execution &
Memory Service", app/services/durable/dbos_engine.py). Needs a real Postgres
database -- set DBOS_TEST_DATABASE_URL to run this file for real; otherwise
it self-skips (matching test_nli_faithfulness.py's pattern for a real,
non-mocked, environment-dependent check).

DBOS registers its workflow/step functions at *module import time* (a
process-wide singleton, not something a fixture can cleanly reset between
tests) -- so unlike the rest of this suite, this file sets its required
environment variables at collection time, before importing dbos_engine, and
runs everything against one shared DBOS instance for the whole file.

generate_content/embed_content are mocked exactly like test_agents.py --
this file is about proving the DBOS orchestration is correct, not about
exercising a real LLM/embedding call.
"""
from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

_DB_URL = os.environ.get("DBOS_TEST_DATABASE_URL", "")
if not _DB_URL:
    pytest.skip(
        "DBOS_TEST_DATABASE_URL not set -- this test needs a real Postgres database "
        "(DBOS has no SQLite mode). See docs/v2/TASKS.md's Durable execution section.",
        allow_module_level=True,
    )

os.environ["DURABLE_EXECUTION_ENABLED"] = "true"
os.environ["DBOS_DATABASE_URL"] = _DB_URL

pytest.importorskip("dbos", reason="dbos not installed -- pip install -r requirements-durable.txt")

from app.agents.graph import run_case_analysis
from app.services.durable.dbos_engine import run_case_analysis_durable

SAMPLE_TEXT = (
    'The Tenant ("Tenant") shall indemnify the Landlord for damages.\n\n'
    "The Tenant shall not sublease the premises without written consent."
)
BORING_TEXT = "The parties will meet quarterly.\n\nNotices go to the addresses in Schedule A."


def _fake_embed_content(contents, model=None):
    return SimpleNamespace(embeddings=[SimpleNamespace(values=[0.1, 0.2, 0.3]) for _ in contents])


@pytest.fixture(autouse=True)
def _mock_model_calls(monkeypatch):
    monkeypatch.setattr("app.agents.summary.generate_content", lambda *a, **k: "Risk summary, no citations.")
    monkeypatch.setattr("app.services.contextualizer.rag.embed_content", _fake_embed_content)
    import app.services.rag.hybrid as hybrid_module
    hybrid_module._dense_index = None
    yield


def test_durable_engine_produces_the_same_result_shape_as_langgraph():
    """The actual "engine-agnostic" proof this roadmap section wants: the
    same AGENT_REGISTRY/planner/CaseState building blocks, driven by two
    different orchestrators, produce the same analysis for the same input."""
    langgraph_result = run_case_analysis(document_id=1, org_id=1, full_text=SAMPLE_TEXT)
    dbos_result = run_case_analysis_durable(document_id=1, org_id=1, full_text=SAMPLE_TEXT)

    assert dbos_result.plan == langgraph_result.plan
    assert dbos_result.ran_steps == langgraph_result.ran_steps
    assert len(dbos_result.clauses) == len(langgraph_result.clauses)
    assert len(dbos_result.risk_findings) == len(langgraph_result.risk_findings)
    assert dbos_result.needs_human_review == langgraph_result.needs_human_review


def test_durable_engine_checkpoints_each_agent_node_as_a_separate_dbos_step():
    from dbos import DBOS

    result = run_case_analysis_durable(document_id=2, org_id=1, full_text=SAMPLE_TEXT)

    workflows = DBOS.list_workflows(name="case_analysis", limit=1, sort_desc=True)
    assert workflows, "expected at least one tracked case_analysis workflow"
    latest = workflows[0]
    assert latest.status == "SUCCESS"

    steps = DBOS.list_workflow_steps(latest.workflow_id)
    step_names = [s["function_name"] for s in steps]
    assert "agent_extraction" in step_names
    for node_id in result.ran_steps:
        if node_id in ("extraction", "planner"):
            continue
        assert f"agent_{node_id}" in step_names


def test_durable_engine_skips_dropped_agents_exactly_like_langgraph():
    langgraph_result = run_case_analysis(document_id=3, org_id=1, full_text=BORING_TEXT)
    dbos_result = run_case_analysis_durable(document_id=3, org_id=1, full_text=BORING_TEXT)

    assert langgraph_result.plan == ["verifier"]
    assert dbos_result.plan == langgraph_result.plan
    assert dbos_result.ran_steps == langgraph_result.ran_steps
