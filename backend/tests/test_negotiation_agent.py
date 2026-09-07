"""
Tests for the Negotiation/Drafting agent -- static org-configured
preferences first (docs/v2/ROADMAP.md Phase 8, LEARNING_LOG.md #51).
No network/model calls: clause_diff and request_human_approval are both
deterministic, stdlib-only tools (app/agents/tools.py).
"""
from app.agents.extraction import run_extraction
from app.agents.negotiation import run_negotiation_drafting
from app.agents.state import CaseState

GOVERNING_LAW_TEXT = "This Agreement shall be governed by the laws of the State of California."
PREFERRED_DELAWARE = "This Agreement shall be governed by the laws of the State of Delaware."


def _state_with_clause(text: str, **kw) -> CaseState:
    state = CaseState(document_id=1, org_id=1, full_text=text)
    state = state.model_copy(update=run_extraction(state))
    return state.model_copy(update=kw)


def test_no_op_when_org_has_no_negotiation_preferences_configured():
    state = _state_with_clause(GOVERNING_LAW_TEXT)

    update = run_negotiation_drafting(state)

    assert update["negotiation_suggestions"] == []
    assert update["trace"][-1].agent_name == "negotiation_drafting"


def test_no_op_when_clause_type_has_no_matching_preference():
    state = _state_with_clause(
        GOVERNING_LAW_TEXT,
        negotiation_preferences={"termination": {"preferred_language": "...", "rationale": "..."}},
    )

    update = run_negotiation_drafting(state)

    assert update["negotiation_suggestions"] == []


def test_no_op_when_clause_already_matches_preferred_language_exactly():
    state = _state_with_clause(
        GOVERNING_LAW_TEXT,
        negotiation_preferences={"governing_law": {"preferred_language": GOVERNING_LAW_TEXT, "rationale": "matches"}},
    )

    update = run_negotiation_drafting(state)

    assert update["negotiation_suggestions"] == []


def test_no_op_when_clause_matches_modulo_whitespace_and_case():
    state = _state_with_clause(
        GOVERNING_LAW_TEXT,
        negotiation_preferences={
            "governing_law": {"preferred_language": "  THIS agreement SHALL be governed   by the laws of the state of california.  ",
                              "rationale": "matches"},
        },
    )

    update = run_negotiation_drafting(state)

    assert update["negotiation_suggestions"] == []


def test_flags_a_high_similarity_but_legally_different_jurisdiction_swap():
    # The real bug this test locks in (LEARNING_LOG.md #51): a one-word
    # jurisdiction change scores 0.90 on difflib's SequenceMatcher ratio --
    # a naive similarity-threshold approach would silently miss exactly the
    # kind of high-value catch this agent exists for.
    state = _state_with_clause(
        GOVERNING_LAW_TEXT,
        negotiation_preferences={
            "governing_law": {"preferred_language": PREFERRED_DELAWARE, "rationale": "Org standard is Delaware law."},
        },
    )

    update = run_negotiation_drafting(state)

    assert len(update["negotiation_suggestions"]) == 1
    suggestion = update["negotiation_suggestions"][0]
    assert suggestion.clause_type == "governing_law"
    assert suggestion.current_language == GOVERNING_LAW_TEXT
    assert suggestion.suggested_language == PREFERRED_DELAWARE
    assert suggestion.rationale == "Org standard is Delaware law."
    assert suggestion.similarity > 0.8  # confirms this really is a "near miss," not a wild diff
    assert suggestion.status == "pending_review"  # never auto-applied
    assert any("Delaware" in line for line in suggestion.diff_lines)


def test_never_auto_applies_a_suggestion():
    # The suggestion is always "pending_review" -- request_human_approval
    # is honestly scoped to not actually block (app/agents/tools.py), so
    # this is really testing that the agent doesn't silently invent a
    # different status implying the edit already happened.
    state = _state_with_clause(
        GOVERNING_LAW_TEXT,
        negotiation_preferences={
            "governing_law": {"preferred_language": PREFERRED_DELAWARE, "rationale": "..."},
        },
    )

    update = run_negotiation_drafting(state)

    assert all(s.status == "pending_review" for s in update["negotiation_suggestions"])
