"""
The Orchestrator/Planner agent (app/agents/planner.py) -- deterministic
rule-based planning + the LLM fallback. No network; the Model Router raises
ModelRouterError with nothing served, which exercises the fallback path.
"""
from __future__ import annotations

import pytest

from app.agents.planner import ANALYSIS_MODES, _rule_plan, run_planner
from app.agents.state import CaseState
from app.services.nlp.schema import AmbiguityFlag, ClauseObject


def _clause(id, text, *, ambiguity=False, terms=None, ctype="other"):
    return ClauseObject(
        id=id, text=text, clause_type=ctype, clause_type_source="rule",
        defined_terms_used=terms or [],
        ambiguity_flags=[AmbiguityFlag(term="reasonable", explanation="vague standard")] if ambiguity else [],
    )


def _state(clauses, **kw):
    return CaseState(document_id=1, org_id=1, clauses=clauses, **kw)


def test_rule_plan_full_with_risk_keyword_is_the_full_pipeline():
    st = _state([_clause(1, "The Provider shall indemnify the Client for all claims.")])
    plan, why = _rule_plan(st, "full")
    assert plan == ["risk_compliance", "research", "summarize"]
    assert "risky-term" in why


def test_rule_plan_full_with_ambiguity_only_still_full():
    st = _state([_clause(1, "The parties will use reasonable efforts.", ambiguity=True)])
    plan, _ = _rule_plan(st, "full")
    assert plan == ["risk_compliance", "research", "summarize"]


def test_rule_plan_benign_document_drops_research_and_summary():
    st = _state([_clause(1, "The parties will meet quarterly to review progress.")])
    plan, why = _rule_plan(st, "full")
    assert plan == []
    assert "structural extraction only" in why


def test_rule_plan_benign_but_with_defined_terms_keeps_the_kg_check():
    st = _state([_clause(1, 'The "Company" and the "Client" will meet quarterly.', terms=["Company", "Client"])])
    plan, why = _rule_plan(st, "full")
    assert plan == ["risk_compliance"]
    assert "KG conflict check only" in why


@pytest.mark.parametrize("mode", list(ANALYSIS_MODES))
def test_rule_plan_honours_every_preset(mode):
    st = _state([_clause(1, "The Provider shall indemnify the Client.")])
    plan, _ = _rule_plan(st, mode)
    assert plan == ANALYSIS_MODES[mode]


def test_run_planner_appends_verifier_and_records_the_trace():
    st = _state([_clause(1, "The Provider shall indemnify the Client.")])
    update = run_planner(st)
    assert update["plan"][-1] == "verifier"
    assert update["plan"] == ["risk_compliance", "research", "summarize", "verifier"]
    assert update["ran_steps"] == ["planner"]
    assert update["trace"][-1].agent_name == "planner"
    assert update["plan_rationale"]


def test_ai_planner_falls_back_to_rule_plan_when_no_model_is_served():
    # conftest leaves EXTERNAL_PROVIDERS_ENABLED=false and no LLM_BASE_URL,
    # so generate_content -> ModelRouterError -> the rule plan is used.
    st = _state([_clause(1, "The Provider shall indemnify the Client.")], use_ai_planner=True)
    update = run_planner(st)
    assert update["plan"] == ["risk_compliance", "research", "summarize", "verifier"]
    assert "ai->rule fallback" in update["plan_rationale"]


def test_unknown_analysis_mode_is_coerced_to_full():
    st = _state([_clause(1, "The Provider shall indemnify the Client.")], analysis_mode="bogus")
    update = run_planner(st)
    assert update["plan"] == ["risk_compliance", "research", "summarize", "verifier"]
