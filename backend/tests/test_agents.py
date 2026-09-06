"""
Tests for the Phase 4 agent pipeline (app/agents/). Gemini calls
(generate_content, embed_content) are mocked throughout, same convention as
test_routes.py -- these tests need no network access or real API key.
Memgraph is unreachable in the test environment (see conftest.py), so
risk_compliance's KG-conflict lookup naturally exercises its fail-soft path.
"""
from types import SimpleNamespace

import pytest

from app.agents.extraction import run_extraction
from app.agents.graph import run_case_analysis
from app.agents.research import run_research
from app.agents.risk_compliance import run_risk_compliance
from app.agents.state import CaseState, RiskFinding
from app.agents.summary import run_summary
from app.agents.verifier import run_verifier

SAMPLE_TEXT = (
    'The Tenant ("Tenant") shall indemnify the Landlord for damages.\n\n'
    "The Tenant shall not sublease the premises without written consent."
)


def fake_embed_content(contents, model=None):
    return SimpleNamespace(embeddings=[SimpleNamespace(values=[0.1, 0.2, 0.3]) for _ in contents])


@pytest.fixture(autouse=True)
def _reset_dense_index():
    # The dense index is a module-level singleton (app/services/rag/hybrid.py)
    # shared across the whole test session. Reset it before every test in
    # this file so a differently-shaped fake embedding used elsewhere (e.g.
    # test_routes.py) can't leave FAISS holding vectors of the wrong
    # dimension when one of these tests runs later in the same session.
    import app.services.rag.hybrid as hybrid_module
    hybrid_module._dense_index = None
    yield


def test_run_extraction_populates_clauses_and_trace():
    state = CaseState(document_id=1, org_id=1, full_text=SAMPLE_TEXT)
    update = run_extraction(state)

    assert len(update["clauses"]) == 2
    assert update["trace"][-1].agent_name == "extraction"


def test_run_risk_compliance_finds_keyword_flag_and_no_kg_conflicts_when_unreachable():
    state = CaseState(document_id=1, org_id=1, full_text=SAMPLE_TEXT)
    state = state.model_copy(update=run_extraction(state))

    update = run_risk_compliance(state)

    terms = {f.term for f in update["risk_findings"]}
    assert "indemnify" in terms
    assert update["kg_conflicts"] == []  # Memgraph unreachable in tests -- fail-soft, not an error


def test_run_research_only_targets_flagged_clauses(monkeypatch):
    monkeypatch.setattr("app.services.contextualizer.rag.embed_content", fake_embed_content)

    state = CaseState(document_id=1, org_id=1, full_text=SAMPLE_TEXT)
    state = state.model_copy(update=run_extraction(state))
    state = state.model_copy(update=run_risk_compliance(state))

    update = run_research(state)

    # Only clauses with a risk finding or ambiguity flag get research citations.
    flagged_ids = {f.clause_id for f in state.risk_findings}
    assert set(update["research_citations"].keys()).issubset(flagged_ids | {c.id for c in state.clauses})


def test_run_summary_skips_generation_when_no_findings(monkeypatch):
    calls = []
    monkeypatch.setattr("app.agents.summary.generate_content", lambda *a, **k: calls.append(1))

    state = CaseState(document_id=1, org_id=1, full_text="Nothing risky here at all.")
    update = run_summary(state)

    assert calls == []
    assert update["summary"] == "No notable risk findings."


def test_run_summary_generates_and_counts_sources(monkeypatch):
    monkeypatch.setattr("app.agents.summary.generate_content", lambda *a, **k: "This is risky [1].")

    state = CaseState(
        document_id=1,
        org_id=1,
        full_text=SAMPLE_TEXT,
        risk_findings=[RiskFinding(clause_id=1, term="indemnify", explanation="...", source="keyword")],
        research_citations={1: [{"text": "Some legal principle.", "topic": "contract_law", "citation": None}]},
    )

    update = run_summary(state)

    assert update["summary"] == "This is risky [1]."
    assert update["summary_citation_count"] == 1


def test_run_verifier_flags_invalid_citation_number():
    state = CaseState(
        document_id=1, org_id=1, summary="This cites [1] and also [9].", summary_citation_count=1,
    )
    update = run_verifier(state)

    assert update["invalid_citation_numbers"] == [9]
    assert update["needs_human_review"] is True


def test_run_verifier_flags_review_when_kg_conflict_present():
    from app.agents.state import KGConflictFinding

    state = CaseState(
        document_id=1, org_id=1, summary="No citations here.", summary_citation_count=0,
        kg_conflicts=[
            KGConflictFinding(
                term="Tenant", obligation_clause="shall pay", prohibition_clause="shall not pay",
                obligation_document_id=1, prohibition_document_id=2,
            )
        ],
    )
    update = run_verifier(state)

    assert update["needs_human_review"] is True


def test_full_graph_runs_end_to_end(monkeypatch):
    monkeypatch.setattr("app.services.contextualizer.rag.embed_content", fake_embed_content)
    monkeypatch.setattr("app.agents.summary.generate_content", lambda *a, **k: "Summary text, no citations.")

    result = run_case_analysis(document_id=1, org_id=1, full_text=SAMPLE_TEXT)

    assert result.document_id == 1
    assert len(result.clauses) == 2
    assert len(result.risk_findings) >= 1
    assert result.summary == "Summary text, no citations."
    agent_names = [step.agent_name for step in result.trace]
    # SAMPLE_TEXT has "indemnify" + "shall not" -> the planner picks the full plan
    assert agent_names == ["extraction", "planner", "risk_compliance", "clause_research", "summary", "verifier"]
    assert result.plan == ["risk_compliance", "research", "summarize", "verifier"]


def test_planner_skips_research_and_summary_for_a_benign_document(monkeypatch):
    calls = []
    monkeypatch.setattr("app.agents.summary.generate_content", lambda *a, **k: calls.append(1))
    monkeypatch.setattr("app.services.contextualizer.rag.embed_content", fake_embed_content)

    result = run_case_analysis(
        document_id=1, org_id=1,
        full_text="The parties will meet quarterly.\n\nNotices go to the addresses in Schedule A.",
    )
    agent_names = [s.agent_name for s in result.trace]
    assert "clause_research" not in agent_names
    assert "summary" not in agent_names
    assert agent_names == ["extraction", "planner", "verifier"]
    assert calls == []
    assert "no risk" in result.plan_rationale.lower()


def test_analysis_mode_extract_only_runs_only_the_gate(monkeypatch):
    monkeypatch.setattr("app.services.contextualizer.rag.embed_content", fake_embed_content)
    result = run_case_analysis(
        document_id=1, org_id=1, full_text=SAMPLE_TEXT, analysis_mode="extract_only",
    )
    assert [s.agent_name for s in result.trace] == ["extraction", "planner", "verifier"]
    assert result.plan == ["verifier"]


def test_analysis_mode_risk_only_skips_the_narrative(monkeypatch):
    calls = []
    monkeypatch.setattr("app.agents.summary.generate_content", lambda *a, **k: calls.append(1))
    result = run_case_analysis(
        document_id=1, org_id=1, full_text=SAMPLE_TEXT, analysis_mode="risk_only",
    )
    agent_names = [s.agent_name for s in result.trace]
    assert agent_names == ["extraction", "planner", "risk_compliance", "verifier"]
    assert result.risk_findings  # the flags are still produced
    assert calls == []
