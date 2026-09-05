"""
Phase 6 cutover-gate gold-set tasks (app/eval/tasks.py): clause_rewrite,
timeline_extract, and risk_analysis previously had no graded eval -- only
`qa` did (LEARNING_LOG.md #21's "follow-up" note). These tests exercise the
scoring logic itself against a controllable stub `generate_fn`, the same way
tests/test_routes.py mocks `generate_content` -- no served model needed.
"""
from app.eval.tasks import run_rewrite_gold, run_risk_analysis_gold, run_timeline_extract_gold


def test_rewrite_gold_scores_a_clean_rewrite_as_perfect():
    from app.eval.gold_set import REWRITE_GOLD

    def good_rewrite(prompt: str) -> str:
        for ex in REWRITE_GOLD:
            if ex["text"] in prompt:
                return "In plain terms: " + ", ".join(ex["must_retain"]) + "."
        return "plain rewrite"

    result = run_rewrite_gold(good_rewrite)
    assert result.score == 1.0
    assert result.extra["retained_fails"] == 0
    assert result.extra["jargon_fails"] == 0


def test_rewrite_gold_penalizes_leftover_jargon():
    def bad_rewrite(prompt: str) -> str:
        # echoes the legalese clause back verbatim -- keeps the jargon it was asked to remove
        return prompt

    result = run_rewrite_gold(bad_rewrite)
    assert result.score < 1.0
    assert result.extra["jargon_fails"] > 0


def test_rewrite_gold_zero_score_when_facts_and_jargon_both_wrong():
    # contains jargon from every example's banned list but none of the retained facts
    always_jargon = (
        "Notwithstanding anything herein, the parties shall indemnify and hold harmless "
        "each other thereafter, hereinafter, and in the then-current term, all obligations "
        "shall be construed in accordance with applicable law, and in no event shall this be limited."
    )
    result = run_rewrite_gold(lambda prompt: always_jargon)
    assert result.score == 0.0


def test_timeline_extract_gold_perfect_when_events_match():
    import json

    from app.eval.gold_set import TIMELINE_GOLD

    def perfect_extractor(prompt: str) -> str:
        for ex in TIMELINE_GOLD:
            if ex["text"] in prompt:
                return json.dumps(ex["expected_events"])
        return "[]"

    result = run_timeline_extract_gold(perfect_extractor)
    assert result.score == 1.0


def test_timeline_extract_gold_zero_when_nothing_returned():
    result = run_timeline_extract_gold(lambda prompt: "[]")
    assert result.score == 0.0


def test_timeline_extract_gold_tolerates_fenced_json():
    import json

    from app.eval.gold_set import TIMELINE_GOLD

    def fenced(prompt: str) -> str:
        for ex in TIMELINE_GOLD:
            if ex["text"] in prompt:
                return "```json\n" + json.dumps(ex["expected_events"]) + "\n```"
        return "[]"

    result = run_timeline_extract_gold(fenced)
    assert result.score == 1.0


def test_risk_analysis_gold_full_recall_when_terms_present():
    import json

    from app.eval.gold_set import RISK_GOLD

    def matching(prompt: str) -> str:
        for ex in RISK_GOLD:
            if ex["text"] in prompt:
                flags = [{"term": t, "explanation": "flagged"} for t in ex["expected_terms"]]
                return json.dumps({"flags": flags})
        return '{"flags": []}'

    result = run_risk_analysis_gold(matching)
    assert result.score == 1.0


def test_risk_analysis_gold_zero_recall_when_no_flags():
    result = run_risk_analysis_gold(lambda prompt: '{"flags": []}')
    assert result.score == 0.0


def test_risk_analysis_gold_handles_unparseable_output():
    result = run_risk_analysis_gold(lambda prompt: "not json at all")
    assert result.score == 0.0
    assert result.n > 0
